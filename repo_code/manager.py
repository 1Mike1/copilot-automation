import bllang
import simplejson
from sqlalchemy import and_

from blconfig import config as blconfig
from blcore.events import notify
from blcore.declarative_base import session
from blnotification.email import queue_email
from blnotification.notification import get_notifications
from utctime import datetime, timedelta

from brighttrac2.base_model import Institution, ExamTypeOffering, Exam, \
    ExamSection
from brighttrac2.base_model.institution_user import \
    InstitutionUserInvitation, ExamTypeAssociation
from brighttrac2.certification.manager import \
    get_delayed_certifications_for_institution
from brighttrac2.note.manager import add_institution_user_note
from brighttrac2.organization_user.core import get_institution_user_state
from brighttrac_NHA.model.model import ProctorDetails, NHAInstitutionUser
from brighttrac_NHA.user.manager import sync_user_with_ahp


def get_help_text(user):
    """Return help text for institution users for various states"""

    language_map = {
        'director_proctor_new': 'C000220',
        'director_proctor_active': 'C000221',
        'director_proctor_expired': 'C000222',
        'instructor_proctor_new': 'C000223',
        'instructor_proctor_active': 'C000224',
        'instructor_proctor_expired': 'C000225',
        'director': 'C000226',
        'instructor': 'C000227',
        'proctor_new': 'C000228',
        'proctor_active': 'C000229',
        'proctor_expired': 'C000230',
    }

    current_state = get_institution_user_state(user)
    token = language_map[current_state]

    _, unseen_notifications_count = get_notifications(user.id, show_seen=False)

    dashboard_data = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'display_name': user.display_name,
        'full_site_url': blconfig.get('full_site_url'),
        'store_url': blconfig.get('store_url'),
        'unseen_notifications_count': unseen_notifications_count
    }

    return bllang.get(token, u'').format(**dashboard_data)


def set_proctor_status_to_expired(proctor_details):
    """Set proctor status to expired and clear out oath and tutorial dates

    Record a user note of proctor details expiration.

    """

    proctor_details.status = 'expired'

    proctor_details.completed_tutorial = None
    proctor_details.taken_oath = None

    note = 'Proctor details status was set to expired.'
    add_institution_user_note(proctor_details.user, note)


def active_proctors_expires_on(expiration_date):
    """Query to get active proctors with given expiration date"""

    return ProctorDetails.query.filter_by(
        status='active', expiration_date=expiration_date
    )


def get_institution_release_exam_types(user):
    """Get institution release exam types user offers at current institution"""

    return [
        offering.exam_type for offering in user.active_exam_types
        if offering.cert_issuance == 'institution_release'
    ]


def queued_delayed_certifications(user):
    """Queued DelayedCertification query for institution user"""
    
    return get_delayed_certifications_for_institution(
        user.active_institution.id,
        exam_type_ids=[
            offering.exam_type_id for offering in user.active_exam_types
        ],
        queued_only=True
    )


def invite_institution_user(user_name, created_by=None, invitation=None, **kw):
    """Invite a user to create an institution user account

    Create an institution user invitation and send them an email with
    invitation key.

    If invitation is passed in, update the existing invitation and resend the
    invitation email.

    """

    invitation_data = {
        'user_name': user_name,
        'created_by': created_by,
    }

    if invitation:
        invitation.update(**invitation_data)
    else:
        invitation = InstitutionUserInvitation(**invitation_data)

    director = kw.pop('roles_director', None)
    proctor = kw.pop('roles_proctor', None)
    instructor = kw.pop('roles_instructor', None)
    roles = [role for role in (director, proctor, instructor) if role]
    associations = simplejson.loads(kw.pop('associations'), '[]')

    invitation.custom_data.update(kw)
    invitation.custom_data.update({
        'roles': roles,
        'associations': associations
    })

    institutions = []
    exam_types = set([])
    for association in associations:
        institution = Institution.get(association.get('institution_id'))
        institutions.append(institution.name)
        offerings = [
            ExamTypeOffering.get(eto_id)
            for eto_id in association.get('exam_type_offerings', [])
        ]
        exam_types.update([eto.exam_type.abbr for eto in offerings])

    user_data = {
        'first_name': kw.get('first_name'),
        'last_name': kw.get('last_name'),
        'user_name': invitation.user_name,
        'institutions': institutions,
        'roles': roles,
        'exam_types': list(exam_types),
        'invitation_key': invitation.invitation_key
    }

    queue_email(email_token='NHA055',
                recipient_list=[invitation.user_name],
                data=user_data)

    return invitation


def get_institution_user_invitation(user_name):
    return InstitutionUserInvitation.get_by(user_name=user_name)


def add_associations(institution_user, associations):
    """Given an associations list associate user to those institutions

    Associations is a list of dictionaries with institution and exam type
    mappings.
    Example Associations Format:

        [
            {
                "institution_id": 2192,
                "exam_type_offerings": [8454, 4356, 7643, 8447]
            }, {
                "institution_id": 1427,
                "exam_type_offerings": [9403, 8062, 8818, 13172, 9405]
            }
        ]

    """

    for association in associations:
        institution = Institution.get(association.get('institution_id'))
        if institution not in institution_user.institutions:
            institution_user.institutions.append(institution)

        for eto_id in association.get('exam_type_offerings'):
            offering = ExamTypeOffering.get(eto_id)
            if offering not in institution_user.exam_type_offerings:
                institution_user.exam_type_associations.append(
                    ExamTypeAssociation(exam_type_offering=offering))


def create_institution_user(invitation, **kw):
    """Create an Institution User from an invitation"""

    institution_user = NHAInstitutionUser(**kw)
    session.flush()

    institution_user.roles = invitation.custom_data.get('roles')

    associations = invitation.custom_data.get('associations', [])
    add_associations(institution_user, associations)

    sync_user_with_ahp(institution_user.id)

    invitation.institution_user = institution_user
    invitation.status = 'accepted'

    notify('clarus.institution_user_created', institution_user)

    return institution_user


def get_upcoming_exams(user):
    """Helper to gather all upcoming exams for an institution user"""

    today = datetime.now().date()

    exams = Exam.query.filter(
        Exam.facility_id.in_([org.facility_id for org in user.organizations])
    ).filter(
        Exam.id.in_(
            session.query(ExamSection.exam_id).filter(
                and_(
                    ExamSection.date >= today,
                    ExamSection.date <= today + timedelta(days=7)
                )
            ).distinct('exam_id')
        )
    )

    return exams
