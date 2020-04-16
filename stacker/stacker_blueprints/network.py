from troposphere import (
    Join,
    NoValue,
    Output,
    Tags,
)
from troposphere import ec2

from stacker.blueprints.base import Blueprint


class Network(Blueprint):
    VARIABLES = {
        "VpcId": {
            "type": str,
            "description": "The Id of the VPC to create the network in.",
        },
        "InternetGatewayId": {
            "type": str,
            "description": "If defined, this network will be a public "
                           "network, and the default route will be through "
                           "the internet gateway. This and NatGatewayId are "
                           "mutually exclusive and cannot be set on the same "
                           "stack.",
            "default": "",
        },
        "CreateNatGateway": {
            "type": bool,
            "description": "If set to true, and no NatGatewayId is specified "
                           "a NatGateway will be created.",
            "default": False,
        },
        "NatGatewayId": {
            "type": str,
            "description": "If defined, this network will be a private "
                           "network, and the default route will be through "
                           "the nat gateway. This and InternetGatewayId are "
                           "mutually exclusive and cannot be set on the same "
                           "stack.",
            "default": "",
        },
        "AvailabilityZone": {
            "type": str,
            "description": "The Availability Zone to create the network in.",
        },
        "CidrBlock": {
            "type": str,
            "description": "The cidr network range to assign the subnet.",
        },
        "Tags": {
            "type": dict,
            "description": "A dictionary of tag key/values to add to all "
                           "resources that accept tags.",
            "default": {},
        },
    }

    @property
    def vpc_id(self):
        return self.get_variables()["VpcId"]

    @property
    def network_type(self):
        if self.internet_gateway_id is not NoValue:
            return "public"
        return "private"

    @property
    def internet_gateway_id(self):
        return self.get_variables()["InternetGatewayId"] or NoValue

    @property
    def nat_gateway_id(self):
        return self.get_variables()["NatGatewayId"] or NoValue

    @property
    def availability_zone(self):
        return self.get_variables()["AvailabilityZone"]

    @property
    def cidr_block(self):
        return self.get_variables()["CidrBlock"]

    @property
    def tags(self):
        variables = self.get_variables()
        tag_dict = {"NetworkType": self.network_type}
        tag_dict.update(variables["Tags"])
        tags = Tags(**tag_dict)
        return tags

    def create_subnet(self):
        t = self.template

        self.subnet = t.add_resource(
            ec2.Subnet(
                "Subnet",
                VpcId=self.vpc_id,
                AvailabilityZone=self.availability_zone,
                CidrBlock=self.cidr_block,
                Tags=self.tags,
            )
        )

        t.add_output(Output("SubnetId", Value=self.subnet.Ref()))
        t.add_output(Output("NetworkType", Value=self.network_type))
        t.add_output(Output("CidrBlock", Value=self.cidr_block))

        attrs = ["AvailabilityZone", "NetworkAclAssociationId", "VpcId"]

        for attr in attrs:
            t.add_output(Output(attr, Value=self.subnet.GetAtt(attr)))

        list_attrs = ["Ipv6CidrBlocks"]

        for attr in list_attrs:
            t.add_output(
                Output(
                    attr,
                    Value=Join(",", self.subnet.GetAtt(attr))
                )
            )

    def create_route_table(self):
        t = self.template

        self.route_table = t.add_resource(
            ec2.RouteTable(
                "RouteTable",
                VpcId=self.vpc_id,
                Tags=self.tags,
            )
        )

        t.add_output(Output("RouteTableId", Value=self.route_table.Ref()))

        self.route_table_assoc = t.add_resource(
            ec2.SubnetRouteTableAssociation(
                "SubnetRouteTableAssociation",
                SubnetId=self.subnet.Ref(),
                RouteTableId=self.route_table.Ref(),
            )
        )

        t.add_output(
            Output(
                "SubnetRouteTableAssociationId",
                Value=self.route_table_assoc.Ref()
            )
        )

    def create_nat_gateway(self):
        t = self.template
        variables = self.get_variables()

        if variables["NatGatewayId"] or not variables["CreateNatGateway"]:
            return

        self.nat_gateway_eip = t.add_resource(
            ec2.EIP(
                "NatGatewayEIP",
                Domain="vpc"
            )
        )

        t.add_output(Output("NatGatewayEIP", Value=self.nat_gateway_eip.Ref()))
        t.add_output(
            Output(
                "NatGatewayEIPAllocationId",
                Value=self.nat_gateway_eip.GetAtt("AllocationId")
            )
        )

        self.nat_gateway = t.add_resource(
            ec2.NatGateway(
                "NatGateway",
                AllocationId=self.nat_gateway_eip.GetAtt("AllocationId"),
                SubnetId=self.subnet.Ref()
            )
        )

        t.add_output(
            Output(
                "NatGatewayId",
                Value=self.nat_gateway.Ref()
            )
        )

    def create_default_route(self):
        t = self.template

        if (self.internet_gateway_id is NoValue and
                self.nat_gateway_id is NoValue):
            # Don't create a default route if no gateway is provided
            # this is a totally private, unreachable network.
            return

        self.default_route = t.add_resource(
            ec2.Route(
                "DefaultRoute",
                RouteTableId=self.route_table.Ref(),
                DestinationCidrBlock="0.0.0.0/0",
                GatewayId=self.internet_gateway_id,
                NatGatewayId=self.nat_gateway_id,
            )
        )

        t.add_output(Output("DefaultRouteId", Value=self.default_route.Ref()))

    def validate_variables(self):
        variables = self.get_variables()
        if (self.internet_gateway_id is not NoValue and
                self.nat_gateway_id is not NoValue):
            raise ValueError("Cannot specify both NatGatewayId and "
                             "InternetGatewayId in the same Network stack.")

        if (variables["CreateNatGateway"] and
                self.nat_gateway_id is not NoValue):
            raise ValueError("Cannot specify both CreateNatGateway as True "
                             "and NatGatewayId in the same Network stack.")

    def create_template(self):
        self.validate_variables()
        self.create_subnet()
        self.create_route_table()
        self.create_nat_gateway()
        self.create_default_route()
