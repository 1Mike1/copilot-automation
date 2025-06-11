from __future__ import print_function
# vim: nu:ts=3:tw=160:wm=2:sw=3:wb
import logging
from datetime import datetime

from turbogears import expose, validate, validators, identity

from blauthentication.utils import exclude_users_with_status
from blconfig import config as blconfig
from blcore.utils.validators import StringBool

from brighttrac2.base_model.exam_type import get_exam_type_group_key
from brighttrac2.model import Institution
from brighttrac2.organization.manager import get_available_exam_type_offerings
from brighttrac2.organization_user.manager import invite_institution_user, \
    get_institution_user_invitation
from brighttrac2.invitations.manager import get_candidate_invitation
from brighttrac2.user_authority.manager import update_user_in_ua
from brighttrac2.subcontrollers.institution import InstitutionController, \
    _institution_validators
from brighttrac2.user import get_user_by_username
from brighttrac2.user.core import sanitize_username
from brighttrac_NHA.model.model import NHAInstitutionUser
from brighttrac_NHA.store_bridge import NHAStoreBridge
from brighttrac_NHA.user.manager import sync_user_with_ahp
from clarus.middleware.csrf import csrf_protect

log = logging.getLogger("brighttrac2.controllers")

_custom_institution_validators = dict(
    waive_institution_shipping_fees=StringBool(if_empty=False),
    institution_shipping_surcharge=validators.Int(),
    candidate_transaction_fee=validators.Number()
)
base_validators = dict(**_institution_validators)
base_validators.pop('tax_exempt', None)


class NHAInstitutionController(InstitutionController):
    controller_name = 'institution'

    @expose()
    @identity.require(identity.has_permission('institutions_edit'))
    @validate(
        validators=dict(
            list(base_validators.items()) + list(_custom_institution_validators.items())
        )
    )
    def update(self, institution_id, **kw):
        return super(
            NHAInstitutionController, self
        ).update(institution_id, **kw)

    @expose()
    def get_default_shipping_method(self, id, **kw):
        i = Institution.get(id)
        return dict(
            success=True,
            default_shipping_method=i.default_shipping_method
        )

    @csrf_protect
    @expose()
    @identity.require(identity.has_permission('institution_users_create'))
    @exclude_users_with_status(
        'suspended',
        'Your account is suspended and you cannot manage users.  '
        'Please contact NHA to resolve this matter.'
    )
    def add_user(self, update_existing=False, user_name=None, **kw):
        """Add an institution user"""

        # FIXME: (NHABT-13939) Remove this function once UA is completed

        if blconfig.get('authentication.ua.enabled'):
            return dict(
                success=False,
                msg='No longer able to create institution users directly. '
                    'Please invite them to register'
            )

        success, data, is_new = self._create_user(
            update_existing=update_existing, cls=NHAInstitutionUser,
            user_name=user_name, **kw
        )

        if success:
            institution_user = data

            # Force the user to reset their password
            sync_user_with_ahp(institution_user.id)
            return dict(success=True)
        else:
            return dict(success=False, **data)

    @expose()
    @identity.require(identity.has_permission('institution_users_create'))
    @exclude_users_with_status(
        'suspended',
        'Your account is suspended and you cannot manage users.  '
        'Please contact NHA to resolve this matter.'
    )
    def invite(self, user_name=None, update_existing=False, **kw):
        """Invite an institution user to create an account"""
        
        user_name = sanitize_username(user_name)

        existing_user = get_user_by_username(user_name)
        if existing_user:
            if existing_user.row_type == 'applicant':
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                updated_user_name = f'{timestamp}_{existing_user.user_name}'
                
                # Update candidate's invitation if any
                existing_invitation = get_candidate_invitation(existing_user.user_name)
                if existing_invitation:
                    existing_invitation.user_name = updated_user_name

                    invite_note = f'Candidate invitation updated from {existing_user.user_name} to {updated_user_name}'
                    existing_user.add_note(invite_note, clarus_identity=identity.current)

                # Update candidate's user_name and email_address
                existing_user.user_name = existing_user.email_address = updated_user_name

                # Update user in UA
                user_data = {'user_name': updated_user_name, 'email': updated_user_name}
                update_user_in_ua(existing_user, user_data)

                note = f'System update: candidate invitation, user_name, and email_address updated ' \
                       f'from {user_name} to {updated_user_name}'
                existing_user.add_note(note, clarus_identity=identity.current)

            else:
                msg = 'A user already exists with this username'
                return dict(success=False, errors={'user_name': msg})
        else:
            # Delete any pending candidate invitation on new user_name
            existing_candidate_invitation = get_candidate_invitation(user_name)
            if existing_candidate_invitation and existing_candidate_invitation.status == 'pending':
                existing_candidate_invitation.delete()

        existing_invitation = get_institution_user_invitation(user_name)
        if existing_invitation and not update_existing:
            return dict(success=False, exists=True)

        invite_institution_user(
            user_name=user_name, created_by=identity.current.user,
            invitation=existing_invitation, **kw
        )

        return dict(success=True, msg='User has been successfully '
                                      'invited to create an account.')

    @expose()
    @identity.require(identity.has_permission('institution_discounts_view'))
    def get_discount_options(self, id):
        nha_store_bridge = NHAStoreBridge(
            blconfig.get('store_url'), blconfig.get('primary_domain')
        )

        i = Institution.get(id)
        options = set()

        offered_abbrs = set()
        for exam_type_offering in i.exam_type_offerings:
            value = get_exam_type_group_key(
                [exam_type_offering.exam_type.abbr]
            )
            options.add(value)
            offered_abbrs.add(exam_type_offering.exam_type.abbr)

        if i.include_packages:
            try:
                packages = nha_store_bridge.get_packages()
                for package in packages:
                    if offered_abbrs.issuperset(package['exam_type']):
                        options.add(
                            get_exam_type_group_key(package['exam_type'])
                        )
            except Exception as e:
                print(e)

        js_options = [dict(description=value) for value in
                      sorted(options, key=lambda v: (len(v), v))]
        return dict(success=True, discount_options=js_options)

    @expose()
    @identity.require(identity.has_permission('institutions_view'))
    def get_exam_type_offerings_for_exams(self, id):
        institution = Institution.get(id)

        exam_type_offerings = get_available_exam_type_offerings(institution)
        return dict(success=True, exam_type_offerings=exam_type_offerings)
