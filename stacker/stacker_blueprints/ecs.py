from awacs.helpers.trust import get_ecs_task_assumerole_policy

from troposphere import (
    ecs,
    iam,
)

from troposphere import (
    NoValue,
    Output,
    Region,
    Sub,
)

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from .policies import ecs_task_execution_policy


class Cluster(Blueprint):
    def create_template(self):
        t = self.template

        cluster = t.add_resource(ecs.Cluster("Cluster"))

        t.add_output(Output("ClusterId", Value=cluster.Ref()))
        t.add_output(Output("ClusterArn", Value=cluster.GetAtt("Arn")))


class BaseECSTask(Blueprint):
    VARIABLES = {
        "TaskName": {
            "type": str,
            "description": "A name for the task/process.",
        },
        "Image": {
            "type": str,
            "description": "The docker image to use for the task.",
        },
        "Command": {
            "type": list,
            "description": "A list of the command and it's arguments to run "
                           "inside the container. If not provided, will "
                           "default to the default command defined in the "
                           "image.",
            "default": [],
        },
        "CPU": {
            "type": int,
            "description": "The relative CPU shares used by each instance of "
                           "the task.",
        },
        "Memory": {
            "type": int,
            "description": "The amount of memory (in megabytes) to reserve "
                           "for each instance of the task.",
        },
        "NetworkMode": {
            "type": str,
            "description": "The NetworkMode to use in the task definition.",
            "default": "",
        },
        "Environment": {
            "type": dict,
            "description": "A dictionary representing the environment of the "
                           "task.",
            "default": {},
        },
        "LogConfiguration": {
            "type": TroposphereType(ecs.LogConfiguration, optional=True),
            "description": "An optional log configuration object. If one is "
                           "not provided, the default is to send logs into "
                           "a Cloudwatch Log LogGroup named after the "
                           "ServiceName",
            "default": None,
        },
        "TaskRoleArn": {
            "type": str,
            "description": "An optional role to run the task as.",
            "default": "",
        },
        "ContainerPort": {
            "type": int,
            "description": "The port of the container to expose to the "
                           "network.  Defaults to not exposing any ports.",
            "default": 0,
        },
        "HostPort": {
            "type": int,
            "description": "The host port to bind to the container port, if "
                           "ContainerPort is specified. If not, does "
                           "nothing. If HostPort is not specified, a dynamic "
                           "port mapping will be used.",
            "default": 0,
        },
        "ContainerProtocol": {
            "type": str,
            "description": "If set, must be either tcp or udp. Requires that "
                           "ContainerPort is set as well. Default: tcp",
            "default": "",
        },
    }

    @property
    def task_name(self):
        return self.get_variables()["TaskName"]

    @property
    def image(self):
        return self.get_variables()["Image"]

    @property
    def command(self):
        return self.get_variables()["Command"] or NoValue

    @property
    def cpu(self):
        return self.get_variables()["CPU"]

    @property
    def task_definition_cpu(self):
        return NoValue

    @property
    def memory(self):
        return self.get_variables()["Memory"]

    @property
    def task_definition_memory(self):
        return NoValue

    @property
    def environment(self):
        env_dict = self.get_variables()["Environment"]
        if not env_dict:
            return NoValue

        env_list = []
        # Sort it first to avoid dict sort issues on different machines
        sorted_env = sorted(env_dict.items(), key=lambda pair: pair[0])
        for k, v in sorted_env:
            env_list.append(ecs.Environment(Name=str(k), Value=str(v)))

        return env_list

    @property
    def log_group_name(self):
        return self.task_name

    @property
    def log_configuration(self):
        log_config = self.get_variables()["LogConfiguration"]
        if not log_config:
            log_config = ecs.LogConfiguration(
                LogDriver="awslogs",
                Options={
                    "awslogs-group": self.log_group_name,
                    "awslogs-region": Region,
                    "awslogs-stream-prefix": self.task_name,
                }
            )
        return log_config

    @property
    def task_role_arn(self):
        return self.get_variables()["TaskRoleArn"]

    @property
    def network_mode(self):
        return self.get_variables()["NetworkMode"] or NoValue

    @property
    def container_port(self):
        return self.get_variables()["ContainerPort"]

    @property
    def host_port(self):
        host_port = self.get_variables()["HostPort"]
        if host_port and not self.container_port:
            raise ValueError("Must specify ContainerPort if specifying "
                             "HostPort")
        return host_port

    @property
    def container_protocol(self):
        container_protocol = self.get_variables()["ContainerProtocol"]
        if container_protocol and not self.container_port:
            raise ValueError("Must specify ContainerPort if specifying "
                             "ContainerProtocol")
        return container_protocol

    @property
    def container_port_mappings(self):
        mappings = NoValue
        if self.container_port:
            kwargs = {"ContainerPort": self.container_port}
            if self.host_port:
                kwargs["HostPort"] = self.host_port
            if self.container_protocol:
                kwargs["Protocol"] = self.container_protocol
            mappings = [ecs.PortMapping(**kwargs)]
        return mappings

    @property
    def container_name(self):
        return self.task_name

    def create_task_role(self):
        if self.task_role_arn:
            self.add_output("RoleArn", self.task_role_arn)
            return

        t = self.template

        self.task_role = t.add_resource(
            iam.Role(
                "Role",
                AssumeRolePolicyDocument=get_ecs_task_assumerole_policy(),
                Path="/",
            )
        )

        self.add_output("RoleName", self.task_role.Ref())
        self.add_output("RoleArn", self.task_role.GetAtt("Arn"))
        self.add_output("RoleId", self.task_role.GetAtt("RoleId"))

    def generate_policy_document(self):
        return None

    def create_task_role_policy(self):
        policy_doc = self.generate_policy_document()
        if self.task_role_arn or not policy_doc:
            return

        t = self.template

        self.task_role_policy = t.add_resource(
            iam.ManagedPolicy(
                "ManagedPolicy",
                PolicyDocument=policy_doc,
                Roles=[self.task_role.Ref()],
            )
        )

        self.add_output("ManagedPolicyArn", self.task_role_policy.Ref())

    def generate_container_definition_kwargs(self):
        kwargs = {
            "Command": self.command,
            "Cpu": self.cpu,
            "Environment": self.environment,
            "Essential": True,
            "Image": self.image,
            "LogConfiguration": self.log_configuration,
            "Memory": self.memory,
            "Name": self.container_name,
            "PortMappings": self.container_port_mappings,
        }

        return kwargs

    def generate_container_definition(self):
        return ecs.ContainerDefinition(
            **self.generate_container_definition_kwargs()
        )

    def generate_task_definition_kwargs(self):
        task_role_arn = self.task_role_arn or self.task_role.GetAtt("Arn")

        return {
            "Cpu": self.task_definition_cpu,
            "Memory": self.task_definition_memory,
            "NetworkMode": self.network_mode,
            "TaskRoleArn": task_role_arn,
            "ContainerDefinitions": [self.generate_container_definition()],
        }

    def create_task_definition(self):
        t = self.template

        self.task_definition = t.add_resource(
            ecs.TaskDefinition(
                "TaskDefinition",
                **self.generate_task_definition_kwargs()
            )
        )

        self.add_output("TaskDefinitionArn", self.task_definition.Ref())

    def create_template(self):
        self.create_task_role()
        self.create_task_role_policy()
        self.create_task_definition()


class SimpleECSTask(BaseECSTask):
    pass


class SimpleFargateTask(BaseECSTask):
    @property
    def network_mode(self):
        network_mode = self.get_variables()["NetworkMode"]
        if network_mode and network_mode != "awsvpc":
            raise ValueError("Fargate services should not set NetworkMode "
                             "('awsvpc' is the only valid mode, and is set "
                             "by default.)")
        return "awsvpc"

    @property
    def task_definition_cpu(self):
        return str(self.cpu)

    @property
    def task_definition_memory(self):
        return str(self.memory)

    def create_task_execution_role(self):
        t = self.template

        self.task_execution_role = t.add_resource(
            iam.Role(
                "TaskExecutionRole",
                AssumeRolePolicyDocument=get_ecs_task_assumerole_policy(),
            )
        )

        t.add_output(
            Output(
                "TaskExecutionRoleName",
                Value=self.task_execution_role.Ref()
            )
        )

        t.add_output(
            Output(
                "TaskExecutionRoleArn",
                Value=self.task_execution_role.GetAtt("Arn")
            )
        )

    def generate_task_execution_policy(self):
        policy_args = {}
        log_config = self.log_configuration
        if log_config.LogDriver == "awslogs":
            policy_args["log_group"] = log_config.Options["awslogs-group"]

        return ecs_task_execution_policy(**policy_args)

    def create_task_execution_role_policy(self):
        t = self.template

        policy_name = Sub("${AWS::StackName}-task-exeuction-role-policy")

        self.task_execution_role_policy = t.add_resource(
            iam.PolicyType(
                "TaskExecutionRolePolicy",
                PolicyName=policy_name,
                PolicyDocument=self.generate_task_execution_policy(),
                Roles=[self.task_execution_role.Ref()],
            )
        )

    def generate_task_definition_kwargs(self):
        kwargs = super(
            SimpleFargateTask, self
        ).generate_task_definition_kwargs()
        kwargs['RequiresCompatibilities'] = ['FARGATE']
        kwargs["ExecutionRoleArn"] = self.task_execution_role.GetAtt("Arn")
        return kwargs

    def create_template(self):
        self.create_task_execution_role()
        self.create_task_execution_role_policy()
        super(SimpleFargateTask, self).create_template()


class BaseECSApp(BaseECSTask):
    """ Combines an ECS Task with an ECS Service for a simple App. """
    def defined_variables(self):
        variables = super(BaseECSApp, self).defined_variables()

        extra_vars = {
            "AppName": {
                "type": str,
                "description": "A simple name for the application.",
            },
            "Cluster": {
                "type": str,
                "description": "The name or Amazon Resource Name (ARN) of the "
                               "ECS cluster that you want to run your tasks "
                               "on.",
            },
            "Count": {
                "type": int,
                "description": "The number of instances of the task to "
                               "create.",
                "default": 1,
            },
            "DeploymentConfiguration": {
                "type": TroposphereType(
                    ecs.DeploymentConfiguration,
                    optional=True
                ),
                "description": "An optional DeploymentConfiguration object.",
                "default": None,
            },
            "PlacementConstraints": {
                "type": TroposphereType(
                    ecs.PlacementConstraint,
                    optional=True,
                    many=True,
                ),
                "description": "An optional list of PlacementConstraint "
                               "objects.",
                "default": None,
            },
            "LoadBalancerTargetGroupArns": {
                "type": list,
                "description": "A list of load balancer target group arns "
                               "to attach to the container. Requires that "
                               "the ContainerPort be set.",
                "default": [],
            },
            "HealthCheckGracePeriodSeconds": {
                "type": int,
                "description": "An optional grace period for load balancer "
                               "health checks against the service when it "
                               "starts up.",
                "default": 0,
            },
        }

        variables.update(extra_vars)
        return variables

    @property
    def app_name(self):
        return self.get_variables()["AppName"]

    @property
    def cluster(self):
        return self.get_variables()["Cluster"]

    @property
    def count(self):
        return self.get_variables()["Count"]

    @property
    def deployment_configuration(self):
        return self.get_variables()["DeploymentConfiguration"] or NoValue

    @property
    def placement_constraints(self):
        return self.get_variables()["PlacementConstraints"] or NoValue

    @property
    def load_balancer_target_group_arns(self):
        arns = self.get_variables()["LoadBalancerTargetGroupArns"]
        if arns and not self.container_port:
            raise ValueError("Must specify ContainerPort if specifying "
                             "LoadBalancerTargetGroupArns")
        return arns

    def generate_load_balancers(self):
        load_balancers = []
        for arn in self.load_balancer_target_group_arns:
            load_balancers.append(
                ecs.LoadBalancer(
                    ContainerName=self.container_name,
                    ContainerPort=self.container_port,
                    TargetGroupArn=arn,
                )
            )
        return load_balancers or NoValue

    @property
    def health_check_grace_period_seconds(self):
        grace_period = self.get_variables()["HealthCheckGracePeriodSeconds"]
        if grace_period and self.generate_load_balancers() is NoValue:
            raise ValueError("Cannot specify HealthCheckGracePeriodSeconds "
                             "without specifying LoadBalancers")
        return grace_period or NoValue

    @property
    def launch_type(self):
        return "EC2"

    @property
    def network_configuration(self):
        return NoValue

    @property
    def log_group_name(self):
        return self.app_name

    def generate_service_kwargs(self):
        grace_period = self.health_check_grace_period_seconds

        config = {
            "Cluster": self.cluster,
            "DeploymentConfiguration": self.deployment_configuration,
            "DesiredCount": self.count,
            "HealthCheckGracePeriodSeconds": grace_period,
            "LaunchType": self.launch_type,
            "LoadBalancers": self.generate_load_balancers(),
            "NetworkConfiguration": self.network_configuration,
            "PlacementConstraints": self.placement_constraints,
            "TaskDefinition": self.task_definition.Ref(),
        }

        return config

    def create_service(self):
        t = self.template
        self.service = t.add_resource(
            ecs.Service("Service", **self.generate_service_kwargs())
        )

        self.add_output("ServiceArn", self.service.Ref())
        self.add_output("ServiceName", self.service.GetAtt("Name"))

    def create_template(self):
        super(BaseECSApp, self).create_template()
        self.create_service()


class SimpleFargateApp(BaseECSApp, SimpleFargateTask):
    def defined_variables(self):
        variables = super(SimpleFargateApp, self).defined_variables()

        additional_variables = {
            "Subnets": {
                "type": list,
                "description": "The list of VPC subnets to deploy the task "
                               "in.",
            },
            "SecurityGroup": {
                "type": str,
                "description": "The SecurityGroup to attach to the task.",
            },
        }

        variables.update(additional_variables)
        return variables

    @property
    def subnets(self):
        return self.get_variables()["Subnets"]

    @property
    def security_group(self):
        return self.get_variables()["SecurityGroup"]

    @property
    def launch_type(self):
        return "FARGATE"

    @property
    def network_configuration(self):
        return ecs.NetworkConfiguration(
            AwsvpcConfiguration=ecs.AwsvpcConfiguration(
                SecurityGroups=[self.security_group],
                Subnets=self.subnets,
            )
        )


class SimpleECSApp(BaseECSApp):
    pass
