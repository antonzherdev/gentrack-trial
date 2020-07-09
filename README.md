## Architecture
```
  S3    =>        Glue           =>     DynamoDb       =>      AppSync 
           consumption_daily_etl    consumption_daily     gentrack_graph_ql
Batches         Spark ETL                                    GraphQL API
```
* A batch of files can go into a folder in S3. A bucket is created for that.
* The Glue ETL collects CSV files from a given S3 folder recursively and aggregates them into DynamoDb. Parameters:
  * s3_path - url inside S3 bucket. By default, it uses a full bucket created in the CloudFormation template.
  * tenant - tenant identifier. Default, 1. 
* DynamoDb contains fields:
  * tenant: int (PartitionKey)
  * date: int (SortKey) - for example 20200607
  * total: int
* AppSync provides an GraphQL endpoint

## Deployment
pipeline.yaml contains a CloudFormation template for CodePipeline.  

The pipeline will deploy the infrastructure using template.yaml.  

It uses GitHub as a source and creates a webhook to trigger pipeline automatically 
if something is pushed to the target branch. For that, it require GitHub authentication token 
which can be created at https://github.com/settings/tokens.

In the create CodePipeline, scroll to last S3 action and press Amazon S3 link. 
It will open the bucket which has been used for the build. 
The `cf.json` will contain:
* RawS3Bucket - the name of created bucked where you can place the raw files.
* GraphQLUrl - URL to call GraphQL API.
* GraphQLApiKey - API key for the GraphQL API.

## How to upload and process files
You can upload to the `{RawS3Bucket}` S3 bucket created for that. 

The files can be placed in a folder to form a batch.

Then the consumption_daily_etl Glue job can be run. 
By default, it processes the full bucket but a folder can be specified in the `s3_path` parameter.    

## How to call API
Using a http client:
* URL: `{GraphQLUrl}`
* Method: POST
* Header: `x-api-key` = `{GraphQLApiKey}`
* Body: GraphQL query serialized in JSON 

To get a paginated list, GraphQL query:
```graphql
query list { 
  listConsumptionDaily(tenant: 1) { 
    items {date total} 
    nextToken 
  }
}
```
JSON form: 
```json
{
  "query": "query list { listConsumptionDaily(tenant: 1) { items {date total} nextToken }}"
}
``` 

## Multi tenancy
Although it was not a requirement to support multi tenancy, 
a partition key is required for DynamoDb.

Date would be a better as a sort key to be able to query a list sorted by date. 
For one default tenant, it will force that all data will be in one partition 
but unless the systems is used for hundred years, it should not be a problem.    

Additionally, it will allow data isolation to run end-to-end testing after deployment in production.

## Files uploading
It's out of the scope for the implementation. Potential solution:
1. API method with tenant id as a parameter
2. It creates a new batch in the S3 folder or uses an existing folder for the tenant. 
The folder name may be calculated based on the current time so that it will be processed in the next processing cycle. `s3://{bucket}/{tenant}/{batch}`. 
3. The API generates a signed URL for the correct folder in the S3 bucket.
4. The client uploads the file directly to S3.
5. A trigger per tenant created for the glue job which will use the batch based on the time of execution or the `s3_path` parameter if presented to enable reprocessing.    

## Todo 
#### Testing
1. End-to-end test
#### Deployment
1. Deploy to staging environment first, make tests and only then to production.
2. Deployment rollback if test fails.
#### Monitoring
1. Glue job failures monitoring using CloudWatch and notifications with SNS.
2. AppSync API failures monitoring using CloudWatch 
#### Security
1. Set only required permissions in the created IAM roles.
2. Change the API Key authentication in AppSync to an appropriate option depending on the clients. 
IAM for other internal services or Cognito or OpenID for external client.
   
  