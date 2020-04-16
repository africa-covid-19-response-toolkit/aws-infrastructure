from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import certificatemanager as acm


class Certificates(Blueprint):
    VARIABLES = {
        "Certificates": {
            "type": TroposphereType(acm.Certificate, many=True),
            "description": "ACM Certificate configurations.",
        },
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()

        for cert in variables["Certificates"]:
            t.add_resource(cert)

            self.add_output("%sId" % cert.title, cert.Ref())
            self.add_output("%sArn" % cert.title, cert.Ref())
