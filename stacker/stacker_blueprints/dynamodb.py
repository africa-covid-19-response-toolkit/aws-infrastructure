from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import (
    iam,
    applicationautoscaling as aas,
    dynamodb,
    Ref,
    GetAtt,
    Output,
    Sub,
)

from .policies import (
    dynamodb_autoscaling_policy,
)

from awacs.helpers.trust import get_application_autoscaling_assumerole_policy


def snake_to_camel_case(name):
    """
    Accept a snake_case string and return a CamelCase string.
    For example::
      >>> snake_to_camel_case('cidr_block')
      'CidrBlock'
    """
    name = name.replace("-", "_")
    return "".join(word.capitalize() for word in name.split("_"))


class DynamoDB(Blueprint):
    """Manages the creation of DynamoDB tables.

    Example::

      - name: users
        class_path: stacker_blueprints.dynamodb.DynamoDB
        variables:
          Tables:
            UserTable:
              TableName: prod-user-table
              KeySchema:
                - AttributeName: id
                  KeyType: HASH
                - AttributeName: name
                  KeyType: RANGE
              AttributeDefinitions:
                - AttributeName: id
                  AttributeType: S
                - AttributeName: name
                  AttributeType: S
              ProvisionedThroughput:
                ReadCapacityUnits: 5
                WriteCapacityUnits: 5
              StreamSpecification:
                StreamViewType: ALL

    """

    VARIABLES = {
        "Tables": {
            "type": TroposphereType(dynamodb.Table, many=True),
            "description": "DynamoDB tables to create.",
        }
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()
        for table in variables["Tables"]:
            t.add_resource(table)
            stream_enabled = table.properties.get("StreamSpecification")
            if stream_enabled:
                t.add_output(Output("{}StreamArn".format(table.title),
                                    Value=GetAtt(table, "StreamArn")))
            t.add_output(Output("{}Name".format(table.title),
                                Value=Ref(table)))


class AutoScaling(Blueprint):
    """Manages the AutoScaling of DynamoDB tables.

    Ref: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dynamodb-table.html#cfn-dynamodb-table-examples-application-autoscaling # noqa

    Example::

      - name: dynamodb-autoscaling
        class_path: stacker_blueprints.dynamodb.AutoScaling
        variables:
          AutoScalingConfigs:

            - table: test-user-table
              read:
                min: 5
                max: 100
                target: 75.0
              write:
                min: 5
                max: 50
                target: 80.0
              indexes:
                - index: index-test-user-table
                  read:
                    min: 5
                    max: 100
                    target: 75.0
                  write:
                    min: 5
                    max: 50
                    target: 80.0

            - table: test-group-table
              read:
                min: 10
                max: 50
                scale-in-cooldown: 180
                scale-out-cooldown: 180
              write:
                max: 25
    """
    VARIABLES = {
        "AutoScalingConfigs": {
            "type": list,
            "description": "A list of dicts, each of which represent "
                           "a DynamoDB AutoScaling Configuration.",
        }
    }

    # reference: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dynamodb-table.html#cfn-dynamodb-table-examples-application-autoscaling # noqa
    def create_scaling_iam_role(self):
        assumerole_policy = get_application_autoscaling_assumerole_policy()
        return self.template.add_resource(
            iam.Role(
                "Role",
                Policies=[
                    iam.Policy(
                        PolicyName=Sub(
                            "${AWS::StackName}-dynamodb-autoscaling"
                        ),
                        PolicyDocument=dynamodb_autoscaling_policy(self.tables)
                    )
                ],
                AssumeRolePolicyDocument=assumerole_policy
            )
        )

    def scalable_resource_name(self, resource, table, capacity_type, index=""):
        camel_table = snake_to_camel_case(table)
        camel_index = snake_to_camel_case(index)

        name = "{}{}{}".format(
            camel_table,
            capacity_type,
            resource,
        )

        if index:
            name = "{}{}{}{}".format(
                camel_table,
                camel_index,
                capacity_type,
                resource,
            )

        return name

    def create_scalable_target_and_scaling_policy(self, table, asc, capacity_type="read", index=""): # noqa
        capacity_type = capacity_type.title()
        if capacity_type not in ("Read", "Write"):
            raise Exception("capacity_type must be either `read` or `write`.")

        dimension = "dynamodb:table:{}CapacityUnits".format(capacity_type)
        if index:
            dimension = "dynamodb:index:{}CapacityUnits".format(capacity_type)

        resource_id = "table/{}".format(table)
        if index:
            resource_id = "{}/index/{}".format(resource_id, index)

        scalable_target_name = self.scalable_resource_name(
            "ScalableTarget", table, capacity_type, index
        )

        scalable_target = self.template.add_resource(
            aas.ScalableTarget(
                scalable_target_name,
                MinCapacity=asc.get("min", 1),
                MaxCapacity=asc.get("max", 1000),
                ResourceId=resource_id,
                RoleARN=self.iam_role_arn,
                ScalableDimension=dimension,
                ServiceNamespace="dynamodb"
            )
        )

        # https://docs.aws.amazon.com/autoscaling/application/APIReference/API_PredefinedMetricSpecification.html # noqa
        predefined_metric_spec = aas.PredefinedMetricSpecification(
            PredefinedMetricType="DynamoDB{}CapacityUtilization".format(
                capacity_type
            )
        )

        ttspc = aas.TargetTrackingScalingPolicyConfiguration(
            TargetValue=asc.get("target", 50.0),
            ScaleInCooldown=asc.get("scale-in-cooldown", 60),
            ScaleOutCooldown=asc.get("scale-out-cooldown", 60),
            PredefinedMetricSpecification=predefined_metric_spec,
        )

        # dynamodb only supports TargetTrackingScaling policy type.
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-applicationautoscaling-scalingpolicy.html#cfn-applicationautoscaling-scalingpolicy-policytype # noqa
        scaling_policy_name = self.scalable_resource_name(
            "ScalablePolicy", table, capacity_type, index
        )
        self.template.add_resource(
            aas.ScalingPolicy(
                scaling_policy_name,
                PolicyName=scaling_policy_name,
                PolicyType="TargetTrackingScaling",
                ScalingTargetId=scalable_target.ref(),
                TargetTrackingScalingPolicyConfiguration=ttspc,
            )
        )

        return scalable_target

    def create_template(self):
        variables = self.get_variables()
        self.auto_scaling_configs = variables["AutoScalingConfigs"]
        self.tables = [config["table"] for config in self.auto_scaling_configs]
        self.iam_role = self.create_scaling_iam_role()
        self.iam_role_arn = GetAtt(self.iam_role, "Arn")
        self.scalable_targets = {}

        for table_asc in self.auto_scaling_configs:

            table_name = table_asc["table"]
            self.scalable_targets[table_name] = {}

            if "read" in table_asc:
                st = self.create_scalable_target_and_scaling_policy(
                    table_name, table_asc["read"], "read"
                )
                self.scalable_targets[table_name]["read"] = st

            if "write" in table_asc:
                st = self.create_scalable_target_and_scaling_policy(
                    table_name, table_asc["write"], "write"
                )
                self.scalable_targets[table_name]["write"] = st

            self.scalable_targets[table_name]["indexes"] = {}

            for index_asc in table_asc.get("indexes", []):

                index = index_asc["index"]
                self.scalable_targets[table_name]["indexes"][index] = {}

                if "read" in index_asc:
                    st = self.create_scalable_target_and_scaling_policy(
                        table_name, table_asc["read"], "read", index
                    )
                    self.scalable_targets[table_name]["indexes"][index]["read"] = st # noqa

                if "write" in index_asc:
                    st = self.create_scalable_target_and_scaling_policy(
                        table_name, table_asc["write"], "write", index
                    )
                    self.scalable_targets[table_name]["indexes"][index]["write"] = st # noqa
