from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import (
    Output,
    Sub,
    iam,
    kinesis,
)

from policies import (
    kinesis_stream_arn,
    read_only_kinesis_stream_policy,
    read_write_kinesis_stream_policy,
)


class Streams(Blueprint):
    VARIABLES = {
        "Streams": {
            "type": TroposphereType(kinesis.Stream, many=True),
            "description": "A dictionary of streams to create. The key "
                           "being the CFN logical resource name, the "
                           "value being a dictionary of attributes for "
                           "the troposphere kinesis.Stream type.",
        },
        "ReadWriteRoles": {
            "type": list,
            "description": "A list of roles that should have read/write "
                           "access to the stream created.",
            "default": []
        },
        "ReadRoles": {
            "type": list,
            "description": "A list of roles that should have read-only "
                           "access to the streams created.",
            "default": []
        },

    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()

        streams = variables["Streams"]
        stream_ids = []

        for stream in streams:
            s = t.add_resource(stream)
            t.add_output(Output("%sStreamId" % stream.title, Value=s.Ref()))
            t.add_output(Output("%sStreamArn" % stream.title,
                                Value=s.GetAtt("Arn")))

            stream_ids.append(s.Ref())

        stream_arns = [kinesis_stream_arn(stream) for stream in stream_ids]

        read_write_roles = variables["ReadWriteRoles"]
        if read_write_roles:
            t.add_resource(
                iam.PolicyType(
                    "ReadWritePolicy",
                    PolicyName=Sub("${AWS::StackName}ReadWritePolicy"),
                    PolicyDocument=read_write_kinesis_stream_policy(
                        stream_arns
                    ),
                    Roles=read_write_roles,
                )
            )

        read_only_roles = variables["ReadRoles"]
        if read_only_roles:
            t.add_resource(
                iam.PolicyType(
                    "ReadPolicy",
                    PolicyName=Sub("${AWS::StackName}ReadPolicy"),
                    PolicyDocument=read_only_kinesis_stream_policy(
                        stream_arns
                    ),
                    Roles=read_only_roles,
                )
            )
