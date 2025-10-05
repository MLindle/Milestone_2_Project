#!/usr/bin/env python3

import boto3, json, os
from datetime import datetime, timezone

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.client('dynamodb')

resume_contents = open("resume_template.md", "r").read()

prompt_template = open("prompt_template.txt", "r").read()

resume_payload = {
    "anthropic_version": "bedrock-2023-05-31",
    "messages": [{
        "role": "user", 
        "content": [{
            "type": "text",
            "text": (
                "This resume is designed for cloud engineering/DevOps. Please convert"
                "it and return the results in valid HTML, in JSON format. Return only"
                " the HTML, no JSON wrapper, no code fences. Please only"
                "include the output for the HTML value starting with <!DOCTYPE html>"
                "to make this easier to use:"
                f"{resume_contents}"
            )
        }]
    }],
    "max_tokens": 4096,
    "temperature": 0
}

response = bedrock.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    body=json.dumps(resume_payload),
    contentType="application/json",
    accept="application/json"
)

bedrock_result_resume= json.loads(response["body"].read())

resume_json_string = json.dumps(bedrock_result_resume)

resume_analytics_payload = {
    "anthropic_version": "bedrock-2023-05-31",
    "messages": [{
        "role": "user",
        "content": [{
            "type": "text",
            "text": (
                f"Can you process this JSON{bedrock_result_resume}"
                "that states an ATS score, word count,"
                "keywords, readability, and missing sections for this resume"
                ", outputting as JSON and using the following format: \n"
                f"{prompt_template}""Please only provide the output in the format"
                "requested with no extra explanation so this can be easily used as"
                "data to be sent to DynamoDB"
            )
        }]
    }],
    "max_tokens": 4096,
    "temperature": 0
}

analytics_response = bedrock.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    body=json.dumps(resume_analytics_payload),
    contentType="application/json",
    accept="application/json"
)

analytics_result = json.loads(analytics_response["body"].read())

br_results = bedrock_result_resume["content"][0]["text"]

analytics_results = json.loads(analytics_result["content"][0]["text"])

for values in analytics_results:
    if values == 'ats_score':
        ats_score = analytics_results.get(values)
    elif values == 'word_count':
        word_count = analytics_results.get(values)
    elif values == 'keywords':
        keywords = analytics_results.get(values)
    elif values == 'readability_score':
        readability_score = analytics_results.get(values)
    elif values == 'missing_sections':
        missing_sections = analytics_results.get(values)

current_utc_datetime = datetime.now(timezone.utc).isoformat()

response = dynamodb.put_item(
    TableName='Milestone-2-project-resume-analytics-table',
    Item={
        'timestamp': {'S': current_utc_datetime},
        'ats_score': {'N': str(ats_score)},
        'word_count': {'N': str(word_count)},
        'keywords': {'SS': keywords}
        }
    
)

github_commit_sha = os.getenv("GITHUB_SHA", "")
deployment_status = os.getenv("DEPLOY_STATUS", "unknown")
deployment_environment = os.getenv("ENVIRONMENT", "")
model_used = "anthropic.claude-3-sonnet"
s3_url = os.getenv("S3_URL", "")

response = dynamodb.put_item(
    TableName='Milestone-2-project-deployment-tracking-table',
    Item={
        'timestamp': {'S': current_utc_datetime},
        'github_commit_sha': {'S': github_commit_sha},
        'deployment_status': {'S': deployment_status},
        'deployment_environment': {'S': deployment_environment},
        'model_used': {'S': model_used},
        's3_url': {'S': s3_url}

        }
)

with open("converted_resume.html", "w") as f:
    f.write(br_results)

