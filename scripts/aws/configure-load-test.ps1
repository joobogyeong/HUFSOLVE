param(
    [ValidateSet("prepare", "restore")]
    [string]$Mode = "prepare",
    [string]$StackName = "hufsolve-core",
    [string]$Profile = "hufsolve-deployer",
    [string]$Region = "ap-northeast-2"
)

$ErrorActionPreference = "Stop"

$outputs = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --profile $Profile `
    --region $Region `
    --query "Stacks[0].Outputs" `
    --output json | ConvertFrom-Json

function Get-StackOutput([string]$key) {
    return ($outputs | Where-Object OutputKey -eq $key).OutputValue
}

$apiAsg = Get-StackOutput "ApiAutoScalingGroupName"
$workerAsg = Get-StackOutput "WorkerAutoScalingGroupName"

if (-not $apiAsg -or -not $workerAsg) {
    throw "Could not resolve API/Worker ASG names from stack outputs."
}

if ($Mode -eq "prepare") {
    $minSize = 1
    $desiredCapacity = 1
} else {
    $minSize = 0
    $desiredCapacity = 0
}

aws autoscaling update-auto-scaling-group `
    --auto-scaling-group-name $apiAsg `
    --min-size $minSize `
    --desired-capacity $desiredCapacity `
    --profile $Profile `
    --region $Region

aws autoscaling update-auto-scaling-group `
    --auto-scaling-group-name $workerAsg `
    --min-size $minSize `
    --desired-capacity $desiredCapacity `
    --profile $Profile `
    --region $Region

aws autoscaling describe-auto-scaling-groups `
    --auto-scaling-group-names $apiAsg $workerAsg `
    --profile $Profile `
    --region $Region `
    --query "AutoScalingGroups[].{Name:AutoScalingGroupName,Min:MinSize,Max:MaxSize,Desired:DesiredCapacity,InService:length(Instances[?LifecycleState=='InService'])}" `
    --output table
