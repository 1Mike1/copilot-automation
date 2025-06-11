Ext6.define('Clarus.admin.system.view.AddStaffUser', {
    extend: 'Ext.container.Container',
    requires: [
        'Clarus.admin.system.view.AddStaffUserController'
        // 'Clarus.view.main.MainController',
        // 'Clarus.view.main.MainModel'
    ],

    xtype: 'admin.system.add-staff-user',

    controller: 'admin.system.view.add-staff-user',
    // viewModel: {
    //     type: 'main'
    // },

    layout: {
        type: 'fit'
    },

    items: [{
        xtype: 'form',
        reference: 'add-staff-user-form',

        frame: true,
        height: '100%',

        defaults:{
            xtype:'textfield',
            anchor: '100%',
            labelWidth: 120
        },
        plugins: [new Ext.ux.AllowBlank()],
        items:[
            { name:'first_name', fieldLabel: 'First Name' },
            { name:'last_name', fieldLabel: 'Last Name' },
            // { name:'user_name', fieldLabel: 'Username (email)' , vtype:'email', allowBlank: false},
            { name:'user_name', fieldLabel: 'Username (email)' , allowBlank: false},
            { name:'password', fieldLabel: 'Password' , inputType:'password', allowBlank: false},
            { name:'password2', fieldLabel: 'Password (confirm)' ,inputType:'password', allowBlank: false},
            {
                xtype: 'label',
                cls: 'x-form-item',
                text: 'By default, this user will not have any permissions within the system.  Please use the Permissions Manager to associate the user with the appropriate groups of permissions.'
            }
        ],

        buttons: [{
            text: 'Add User',
            listeners: {
                click: "onAddStaffUser"

            }
        }]
    }]

});
