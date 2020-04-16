from stacker.blueprints.base import Blueprint

from troposphere import (
    GetAtt,
    Output,
    Ref,
    Sub,
    iam,
)

from awacs.aws import Policy
from awacs.helpers.trust import (
    get_default_assumerole_policy,
    get_lambda_assumerole_policy
)


class RoleBaseBlueprint(Blueprint):

    def __init__(self, *args, **kwargs):
        super(RoleBaseBlueprint, self).__init__(*args, **kwargs)
        self.roles = []
        self.policies = []

    def create_role(self, name, policy):
        raise NotImplementedError

    def create_ec2_role(self, name):
        return self.create_role(name, get_default_assumerole_policy())

    def create_lambda_role(self, name):
        return self.create_role(name, get_lambda_assumerole_policy())

    def generate_policy_statements(self):
        """Should be overridden on a subclass to create policy statements.

        By subclassing this blueprint, and overriding this method to generate
        a list of :class:`awacs.aws.Statement` types, a
        :class:`troposphere.iam.PolicyType` will be created and attached to
        the roles specified here.

        If not specified, no Policy will be created.
        """

        return []

    def create_policy(self, name=None):
        statements = self.generate_policy_statements()
        if not statements:
            return

        t = self.template

        logical_name = "Policy"
        if name:
            logical_name = "{}Policy".format(name)
            policy_name = Sub("${AWS::StackName}-${Name}-policy", Name=name)
        else:
            policy_name = Sub("${AWS::StackName}-policy")

        policy = t.add_resource(
            iam.PolicyType(
                logical_name,
                PolicyName=policy_name,
                PolicyDocument=Policy(
                    Statement=statements,
                ),
                Roles=[Ref(role) for role in self.roles],
            )
        )

        t.add_output(
            Output("PolicyName", Value=Ref(policy))
        )
        self.policies.append(policy)
        return policy


class Ec2Role(RoleBaseBlueprint):
    """
    Blueprint to create an Ec2 role.

    - class_path: stacker_blueprints.iam_roles.Ec2Role
      name: my-role
        variables:
          AttachedPolicies:
          - arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
          InstanceProfile: True
          Name: myRole
          Path: /
    """
    VARIABLES = {
        "AttachedPolicies": {
            "type": list,
            "description": "List of ARNs of policies to attach",
            "default": [],
        },
        "InstanceProfile": {
            "type": bool,
            "description": "The role is an instance profile.",
            "default": False,
        },
        "Name": {
            "type": str,
            "description": "The name of the role",
            "default": "Role",
        },
        "Path": {
            "type": str,
            "description": "Provide the path",
            "default": "",
        },
    }

    def create_role(self, name, assumerole_policy):
        t = self.template
        v = self.get_variables()

        role_kwargs = {
            'AssumeRolePolicyDocument': assumerole_policy,
        }

        attached_policies = v['AttachedPolicies']
        if attached_policies:
            role_kwargs['ManagedPolicyArns'] = attached_policies

        path = v['Path']
        if path:
            role_kwargs['Path'] = path

        role = t.add_resource(
            iam.Role(
                name,
                **role_kwargs
            )
        )

        t.add_output(
            Output(name + "RoleName", Value=Ref(role))
        )

        t.add_output(
            Output(name + "RoleArn", Value=GetAtt(role.title, "Arn"))
        )

        if v['InstanceProfile']:
            profile_kwargs = {
                'Roles': [
                    Ref(role),
                ],
            }

            if path:
                profile_kwargs['Path'] = path

            instance_profile = t.add_resource(
                iam.InstanceProfile(
                    name + 'InstanceProfile',
                    **profile_kwargs
                )
            )

            t.add_output(
                Output("InstanceProfileName", Value=Ref(instance_profile))
            )

            t.add_output(
                Output(
                    "InstanceProfileArn",
                    Value=GetAtt(instance_profile.title, "Arn")
                )
            )

        self.roles.append(role)
        return role

    def create_template(self):
        v = self.get_variables()
        self.create_ec2_role(v["Name"])
        self.create_policy(v["Name"])


class Roles(RoleBaseBlueprint):
    """
    Blueprint to create many Ec2 and Lambda roles.
    """
    VARIABLES = {
        "Ec2Roles": {
            "type": list,
            "description": "names of ec2 roles to create",
            "default": [],
        },
        "LambdaRoles": {
            "type": list,
            "description": "names of lambda roles to create",
            "default": [],
        },
    }

    def create_role(self, name, assumerole_policy):
        t = self.template

        role = t.add_resource(
            iam.Role(
                name,
                AssumeRolePolicyDocument=assumerole_policy,
            )
        )

        t.add_output(
            Output(name + "RoleName", Value=Ref(role))
        )
        t.add_output(
            Output(name + "RoleArn", Value=GetAtt(role.title, "Arn"))
        )

        self.roles.append(role)
        return role

    def create_template(self):
        variables = self.get_variables()

        for role in variables['Ec2Roles']:
            self.create_ec2_role(role)

        for role in variables['LambdaRoles']:
            self.create_lambda_role(role)

        self.create_policy()
