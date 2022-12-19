# CloudFormation Custom Resource to deploy and attach SageMaker Studio Lifecycle Config

## Disclaimer

**This project is used for demo purposes only and should NOT be considered for production use.**

## Overview

This repository contains SAM template to provision the following resources:
- Lambda function that creates SM Studio Lifecycle Config (LCC) and attaches it to a SM Studio Domain. The sample LCC disables JupyterLab extensions to remove download buttons from the JupyterLab UI.
  - The LCC script can be found at the top of the Lambda Python script.
- IAM Role for the Lambda function
- CloudFormation Custom Resource that invokes the Lambda function

The Lambda function code can be found in the `lambda_lcc` folder - `create_attach_studio_lcc.py` file. Note that during Cfn creation it will create and attach the LCC to SM Studio Domain, and during Cfn deletion it will detach and delete the LCC.

This repository uses AWS Serverless Application Model (SAM) to deploy the resources. See [this page](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for more information about SAM. You can use CloudFormation to deploy it as well. SAM is used because it provides a convenient way to package the Lambda function into the template.

### Template Parameters

1. StudioLCCName: name of the Lifecycle Configuration that will be created
1. SMStudioDomainId: the domain ID of SageMaker Studio Domain that the LCC will be attached to

## Deployment 

### Pre-requisites

1. Installed [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) and [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
2. AWS Credentials (IAM User or Role) to the account where the resources will be deployed.

### Deployment Steps

1. Run the following commands:
    ```sh
    # build the template. this command needs to be run every time you update the template or lambda function.
    sam build
    # deploys resources to the AWS account. You will need to fill in the parameters specified in the template.
    sam deploy --guided
    ```

