import os
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client("ec2")

def handler(event, context):
    """
    Automated FinOps Lambda Handler (Rule 2.3)
    Triggered daily via Amazon EventBridge schedule to stop the EC2 instance
    if inadvertently left running, preventing cloud bill shock.
    """
    instance_id = os.environ.get("INSTANCE_ID")
    if not instance_id:
        logger.error("INSTANCE_ID environment variable is missing.")
        return {"status": "error", "message": "INSTANCE_ID environment variable is missing"}

    logger.info(f"Inspecting state for target instance: {instance_id}")
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        reservations = response.get("Reservations", [])
        if not reservations or not reservations[0].get("Instances"):
            logger.error(f"Target instance {instance_id} was not found.")
            return {"status": "error", "message": f"Instance {instance_id} not found"}

        current_state = reservations[0]["Instances"][0]["State"]["Name"]
        logger.info(f"Current instance state is: '{current_state}'")

        if current_state == "running":
            logger.info(f"Instance is currently running. Issuing StopInstances command to {instance_id}...")
            ec2.stop_instances(InstanceIds=[instance_id])
            logger.info(f"Successfully sent StopInstances signal to {instance_id}.")
            return {
                "status": "success",
                "action": "stopped",
                "instance_id": instance_id,
                "previous_state": current_state
            }
        else:
            logger.info(f"Instance is already in '{current_state}' state. No shutdown required.")
            return {
                "status": "noop",
                "action": "none",
                "instance_id": instance_id,
                "current_state": current_state
            }
    except Exception as e:
        logger.error(f"Failed to inspect or stop instance {instance_id}: {str(e)}")
        raise e
