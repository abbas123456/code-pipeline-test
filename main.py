import os

from troposphere import Base64, FindInMap, GetAtt, Join, Output, Sub, Parameter, Ref, ImportValue, Export,Template, Select, Split, Region
import troposphere.ec2 as ec2
import troposphere.ecs as ecs
import troposphere.iam as iam
import troposphere.logs as logs
import troposphere.cloudwatch as cloudwatch
import troposphere.elasticloadbalancingv2 as elb
import troposphere.autoscaling as autoscaling
import troposphere.s3 as s3

def main():
    template = Template()

    template.add_resource(ecs.Cluster(
        "ECSCluster",
        ClusterName="WorldCheckCluster"
    ))

    template.add_resource(iam.Role(
        "ECSTaskRole",
        AssumeRolePolicyDocument={
           "Version" : "2012-10-17",
           "Statement": [ {
              "Effect": "Allow",
              "Principal": {
                 "Service": [ "ecs-tasks.amazonaws.com" ]
              },
              "Action": [ "sts:AssumeRole" ]
           } ]
        }
    ))

    template.add_resource(iam.Role(
        "ECSServiceSchedulerRole",
        AssumeRolePolicyDocument={
           "Version" : "2012-10-17",
           "Statement": [ {
              "Effect": "Allow",
              "Principal": {
                 "Service": [ "ecs.amazonaws.com" ]
              },
              "Action": [ "sts:AssumeRole" ]
           } ]
        },
        Policies=[iam.Policy(
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ec2:Describe*",
                            "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
                            "elasticloadbalancing:DeregisterTargets",
                            "elasticloadbalancing:Describe*",
                            "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
                            "elasticloadbalancing:RegisterTargets"
                        ],
                        "Resource": "*"
                    }
                ]
            },
            PolicyName="ecs-service"
        )]
    ))

    template.add_resource(iam.Role(
        "EC2InstanceRole",
        AssumeRolePolicyDocument={
           "Version" : "2012-10-17",
           "Statement": [ {
              "Effect": "Allow",
              "Principal": {
                 "Service": [ "ec2.amazonaws.com" ]
              },
              "Action": [ "sts:AssumeRole" ]
           } ]
        },
        Policies=[iam.Policy(
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "ecs:CreateCluster",
                            "ecs:DeregisterContainerInstance",
                            "ecs:DiscoverPollEndpoint",
                            "ecs:Poll",
                            "ecs:RegisterContainerInstance",
                            "ecs:StartTelemetrySession",
                            "ecr:GetAuthorizationToken",
                            "ecr:BatchGetImage",
                            "ecr:GetDownloadUrlForLayer",
                            "ecs:Submit*",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "ec2:DescribeTags",
                            "cloudwatch:PutMetricData"
                        ],
                        "Resource": "*"
                    }
                ]
            },
            PolicyName="ecs-service"
        )]
    ))
    template.add_resource(iam.InstanceProfile(
        "EC2InstanceProfile",
        Roles=[Ref("EC2InstanceRole")]
    ))

    with open("user-data.sh", "r") as f:
        user_data_content = f.readlines()

    template.add_resource(ec2.Instance(
        "EC2Instance",
        ImageId="ami-13f7226a",
        InstanceType="t2.micro",
        SecurityGroups=["default"],
        UserData=Base64(Join('',[Sub(x) for x in user_data_content])),
        IamInstanceProfile=Ref("EC2InstanceProfile"),
    ))

    template.add_resource(ecs.TaskDefinition(
        "ECSTaskDefinition",
        TaskRoleArn=Ref("ECSTaskRole"),
        ContainerDefinitions=[ecs.ContainerDefinition(
            Name="SimpleServer",
            Memory="128",
            Image="abbas123456/simple-server:latest",
            PortMappings=[ecs.PortMapping(
                ContainerPort=8000
            )],
        )]
    ))

    template.add_resource(elb.TargetGroup(
        "ECSTargetGroup",
        VpcId="vpc-925497f6",
        Port=8000,
        Protocol="HTTP",
    ))

    template.add_resource(elb.LoadBalancer(
        "LoadBalancer",
        Subnets=["subnet-a321c8fb", "subnet-68fa271e", "subnet-689d350c"],
        SecurityGroups=["sg-0202bd65"]
    ))

    template.add_resource(elb.Listener(
        "LoadBalancerListener",
        DefaultActions=[elb.Action(
            Type="forward",
            TargetGroupArn=Ref("ECSTargetGroup")
        )],
        LoadBalancerArn=Ref("LoadBalancer"),
        Port=80,
        Protocol="HTTP",
    ))

    template.add_resource(ecs.Service(
        "ECSService",
        Cluster=Ref("ECSCluster"),
        DesiredCount=1,
        LoadBalancers=[ecs.LoadBalancer(
            ContainerPort=8000,
            ContainerName="SimpleServer",
            TargetGroupArn=Ref("ECSTargetGroup")
        )],
        Role=Ref("ECSServiceSchedulerRole"),
        TaskDefinition=Ref("ECSTaskDefinition"),
        DependsOn="LoadBalancerListener"
    ))

    return template.to_json()

if __name__ == "__main__":
    with open("stack.json", "w+") as f:
        f.write(main())
