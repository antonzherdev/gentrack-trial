import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame

glueContext = GlueContext(SparkContext.getOrCreate())

##############################################################################################################
# Parameters
##############################################################################################################
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'tenant', 's3_path'])
tenant = int(args['tenant'])
s3_path = args['s3-path']

##############################################################################################################
# Extract
##############################################################################################################
source_df = glueContext.create_dynamic_frame_from_options(
    connection_type="s3",
    format="csv",
    connection_options={
        "paths": [s3_path],
        "recurse": True
    },
    format_options={
        "withHeader": True,
        "separator": ","
    })


##############################################################################################################
# Transform 1: Totals in rows
##############################################################################################################
def calc_total(rec):
    total = 0
    for i in range(0, 24):
        total += int(rec[str(i) + ":00"]) + int(rec[str(i) + ":30"])
        del rec[str(i) + ":00"]
        del rec[str(i) + ":30"]
    rec["tenant"] = tenant
    rec["date"] = int(rec["Date"].replace("-", ""))
    rec["total"] = total
    del rec["Meter"]
    del rec["Date"]
    return rec


mapped_df = Map.apply(frame=source_df, f=calc_total)

##############################################################################################################
# Transform 2: Aggregate total
##############################################################################################################
aggregated_df = DynamicFrame.fromDF(
    mapped_df.toDF().groupBy('tenant', 'date').sum('total'), glueContext, "result"
).rename_field("sum(total)", "total")

##############################################################################################################
# Load
##############################################################################################################
glueContext.write_dynamic_frame.from_options(
    frame=aggregated_df,
    connection_type="dynamodb",
    connection_options={"dynamodb.output.tableName": "consumption_daily"})
