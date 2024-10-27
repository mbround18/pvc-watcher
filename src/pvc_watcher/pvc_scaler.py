import kopf
import kubernetes.client
from kubernetes.client.rest import ApiException
import time
from kubernetes import config
import os

CHECK_INTERVAL = 30

if not os.getenv("KUBERNETES_SERVICE_HOST") or not os.getenv("KUBERNETES_SERVICE_PORT"):
    kopf.event(
        objs=[],
        type="Warning",
        reason="EnvVarsMissing",
        message="Kubernetes service host or port environment variables are not set. Ensure the container is running inside Kubernetes.",
    )

try:
    config.load_incluster_config()
except Exception as e:
    kopf.event(
        objs=[],
        type="Warning",
        reason="InClusterConfigError",
        message=f"Failed to load in-cluster configuration: {e}",
    )


def get_deployment(api_instance, name, namespace):
    try:
        return api_instance.read_namespaced_deployment(name, namespace)
    except ApiException as e:
        kopf.event(
            objs=[],
            type="Warning",
            reason="DeploymentReadError",
            message=f"Exception when reading deployment: {e}",
        )
        return None


def scale_deployment(api_instance, name, namespace, replicas, event_message=None):
    body = {"spec": {"replicas": replicas}}
    try:
        patched = api_instance.patch_namespaced_deployment_scale(name, namespace, body)
        kopf.event(
            objs=patched,
            type="Normal",
            reason="DeploymentScaled",
            message=(
                event_message
                if event_message
                else f"Scaled deployment {name} to {replicas} replicas."
            ),
        )
    except ApiException as e:
        kopf.event(
            objs=get_deployment(api_instance, name, namespace),
            type="Warning",
            reason="DeploymentScaleError",
            message=f"Exception when scaling deployment: {e}",
        )


@kopf.timer("persistentvolumeclaims", interval=CHECK_INTERVAL)
def pvc_monitoring(spec, name, namespace, status, **kwargs):
    phase = status.get("phase")
    if phase in ["Failed", "ReadOnly"]:
        kopf.event(
            objs=kwargs["body"],
            type="Warning",
            reason="PVCReadOnly",
            message=f"PVC {name} is in {phase} state. Scaling down associated deployment.",
        )

        api_instance = kubernetes.client.AppsV1Api()
        deployment_name = name.replace("-pvc", "")
        deployment = get_deployment(api_instance, deployment_name, namespace)
        if deployment:
            original_replicas = deployment.spec.replicas
            scale_deployment(
                api_instance,
                deployment_name,
                namespace,
                0,
                event_message=f"Scaling deployment {deployment_name} to 0 replicas due to PVC being in read-only state.",
            )

            core_v1_api = kubernetes.client.CoreV1Api()
            while phase in ["Failed", "ReadOnly"]:
                time.sleep(CHECK_INTERVAL)
                pvc = core_v1_api.read_namespaced_persistent_volume_claim(
                    name, namespace
                )
                phase = pvc.status.phase

            kopf.event(
                objs=kwargs["body"],
                type="Normal",
                reason="PVCBackToNormal",
                message=f"PVC {name} is back to normal state. Scaling up deployment {deployment_name}.",
            )
            scale_deployment(
                api_instance,
                deployment_name,
                namespace,
                original_replicas,
                event_message=f"Scaling deployment {deployment_name} back to {original_replicas} replicas as PVC is back to normal.",
            )
