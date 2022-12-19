import boto3
import botocore
import urllib3
import json
import base64

SUCCESS = "SUCCESS"
FAILED = "FAILED"

http = urllib3.PoolManager()


LCC_CONTENT = '''
echo '{' > /opt/conda/envs/studio/etc/jupyter/labconfig/page_config.json
echo '  "disabledExtensions": {' >> /opt/conda/envs/studio/etc/jupyter/labconfig/page_config.json
echo '    "@jupyterlab/filebrowser-extension:share-file": true,' >> /opt/conda/envs/studio/etc/jupyter/labconfig/page_config.json
echo '    "@jupyterlab/scheduler:IAdvancedOptions": true,' >> /opt/conda/envs/studio/etc/jupyter/labconfig/page_config.json
echo '    "@jupyterlab/docmanager-extension:download": true,' >> /opt/conda/envs/studio/etc/jupyter/labconfig/page_config.json
echo '    "@jupyterlab/filebrowser-extension:download": true' >> /opt/conda/envs/studio/etc/jupyter/labconfig/page_config.json
echo '  }' >> /opt/conda/envs/studio/etc/jupyter/labconfig/page_config.json
echo '}' >> /opt/conda/envs/studio/etc/jupyter/labconfig/page_config.json
restart-jupyter-server
'''

def handler(event, context):
    print(event)

    # init vars
    response_data = {}
    response_status = FAILED
    sm = boto3.client('sagemaker')
    lcc_name = event['ResourceProperties']['LCCName']
    studio_domain_id = event['ResourceProperties']['DomainId']

    if event['RequestType'] == 'Create':
        response_data = create_attach_studio_lcc(sm, lcc_name, LCC_CONTENT, studio_domain_id, response_data)
        if 'Error' not in response_data.keys():
            response_data['Message'] = f'Studio LCC ({response_data["lcc_arn"]}) has been created and attached to Studio domain {studio_domain_id}!'
            response_status = SUCCESS

    elif event['RequestType'] == 'Update':
        response_data['Message'] = "Nothing to be done during Update!"
        response_status = SUCCESS

    elif event['RequestType'] == 'Delete':
        # Need to empty the S3 bucket before it is deleted
        response_data = detach_delete_studio_lcc(sm, lcc_name, studio_domain_id, response_data)
        if 'Error' not in response_data.keys():
            response_data['Message'] = "Studio LCC deletion successful."
            response_status = SUCCESS

    send(event, context, response_status, response_data)

def create_attach_studio_lcc(sm, lcc_name, lcc_content, domain_id, response_data):
    # create LCC

    message_bytes = lcc_content.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('ascii')
    try:
        response = sm.create_studio_lifecycle_config(
            StudioLifecycleConfigName=lcc_name,
            StudioLifecycleConfigContent=base64_message,
            StudioLifecycleConfigAppType='JupyterServer'
        )
        lcc_arn = response['StudioLifecycleConfigArn']
        response_data['lcc_arn'] = lcc_arn
    except botocore.exceptions.ClientError as e:
        message = 'Error while creating SM Studio LCC.'
        print(message)
        print(e.response['Error']['Code'])
        print(e.response['Error']['Message'])
        response_data['Error'] = message
        return response_data

    # attach LCC to SM Domain
    try:
        response = sm.update_domain(
            DomainId=domain_id,
            DefaultUserSettings={
                'JupyterServerAppSettings': {
                    'DefaultResourceSpec': {
                        'LifecycleConfigArn': lcc_arn
                    },
                    'LifecycleConfigArns': [lcc_arn]
                },
            }
        )
    except botocore.exceptions.ClientError as e:
        message = 'Error while attaching SM Studio LCC to SM Domain.'
        print(message)
        print(e.response['Error']['Code'])
        print(e.response['Error']['Message'])
        response_data['Error'] = message
        return response_data

    return response_data

def detach_delete_studio_lcc(sm, lcc_name, domain_id, response_data):
    # get LCC ARN
    try:
        response = sm.describe_studio_lifecycle_config(
            StudioLifecycleConfigName=lcc_name
        )
        lcc_arn = response['StudioLifecycleConfigArn']
    except botocore.exceptions.ClientError as e:
        message = 'Error while describiing SM Studio LCC.'
        print(message)
        print(e.response['Error']['Code'])
        print(e.response['Error']['Message'])
        response_data['Error'] = message
        return response_data

    # detach LCC from SM Studio Domain
    try:
        response = sm.update_domain(
            DomainId=domain_id,
            DefaultUserSettings={
                'JupyterServerAppSettings': {
                    'DefaultResourceSpec': {
                        'LifecycleConfigArn': lcc_arn
                    },
                    'LifecycleConfigArns': []
                },
            }
        )
    except botocore.exceptions.ClientError as e:
        message = 'Error while detaching SM Studio LCC to SM Domain.'
        print(message)
        print(e.response['Error']['Code'])
        print(e.response['Error']['Message'])
        response_data['Error'] = message
        return response_data

    # delete LCC
    try:
        sm.delete_studio_lifecycle_config(
            StudioLifecycleConfigName=lcc_name
        )
    except botocore.exceptions.ClientError as e:
        message = 'Error while deleting SM Studio LCC.'
        print(message)
        print(e.response['Error']['Code'])
        print(e.response['Error']['Message'])
        response_data['Error'] = message
        return response_data

    return response_data


def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
    responseUrl = event['ResponseURL']

    print(responseUrl)

    responseBody = {
        'Status' : responseStatus,
        'Reason' : reason or "See the details in CloudWatch Log Stream: {}".format(context.log_stream_name),
        'PhysicalResourceId' : physicalResourceId or context.log_stream_name,
        'StackId' : event['StackId'],
        'RequestId' : event['RequestId'],
        'LogicalResourceId' : event['LogicalResourceId'],
        'NoEcho' : noEcho,
        'Data' : responseData
    }

    json_responseBody = json.dumps(responseBody)

    print("Response body:")
    print(json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
        print("Status code:", response.status)


    except Exception as e:

        print("send(..) failed executing http.request(..):", e)
