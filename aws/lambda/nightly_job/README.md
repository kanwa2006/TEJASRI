# Nightly Job Lambda

Creates daily `adherence_check` tasks for active care plans and archives
yesterday's audit log to S3. Stays inside the AWS always-free tier
(1M requests + 400k GB-s/month); runs once per day.

## Deploy (zip-based, no framework required)

```bash
cd aws/lambda/nightly_job
pip install --target package asyncpg          # boto3 ships in the Lambda runtime
cp handler.py package/
cd package && zip -r ../nightly_job.zip . && cd ..

aws lambda create-function \
  --function-name tejasri-nightly-job \
  --runtime python3.12 \
  --handler handler.lambda_handler \
  --zip-file fileb://nightly_job.zip \
  --role arn:aws:iam::<account>:role/tejasri-lambda-role \
  --timeout 60 --memory-size 256 \
  --environment "Variables={DATABASE_URL=postgresql://tejasri_app:...,S3_BUCKET=<bucket>}"

# nightly at 02:00 UTC
aws events put-rule --name tejasri-nightly --schedule-expression "cron(0 2 * * ? *)"
aws lambda add-permission --function-name tejasri-nightly-job \
  --statement-id eventbridge --action lambda:InvokeFunction \
  --principal events.amazonaws.com
aws events put-targets --rule tejasri-nightly \
  --targets "Id"="1","Arn"="<lambda-arn>"
```

## IAM (least privilege)

The `tejasri-lambda-role` needs only:
- `AWSLambdaBasicExecutionRole` (CloudWatch logs)
- `s3:PutObject` on `arn:aws:s3:::<bucket>/audit-archive/*`

## Cost guards

- Do **not** attach the function to a VPC (avoids NAT-gateway cost) — it
  reaches CockroachDB Cloud and S3 over public HTTPS.
- Keep the $1 AWS Budget alert active (see docs/DEPLOYMENT.md).

## Local dry run

```bash
DATABASE_URL=postgresql://tejasri_app@localhost:26257/defaultdb?sslmode=disable \
  python handler.py
```
