from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.transforms import DropNullFields
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import functions as F


required_args = ["JOB_NAME", "source_path", "target_path"]
args = getResolvedOptions(__import__("sys").argv, required_args)

spark_context = SparkContext()
glue_context = GlueContext(spark_context)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

source_dynamic_frame = glue_context.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [args["source_path"]]},
    format="csv",
    format_options={"withHeader": True, "separator": ","},
)

nonnull_dynamic_frame = DropNullFields.apply(frame=source_dynamic_frame)
source_df = nonnull_dynamic_frame.toDF()

deduplicated_df = source_df.dropDuplicates()

feature_df = (
    deduplicated_df.withColumn("Amount", F.col("Amount").cast("double"))
    .withColumn("log_amount", F.log1p(F.col("Amount")))
    .withColumn("event_ts", F.current_timestamp())
    .withColumn("hour_bin", F.hour(F.col("event_ts")))
    .withColumn(
        "amount_percentile_bin",
        F.when(F.col("Amount") < 10.0, F.lit("low"))
        .when(F.col("Amount") < 100.0, F.lit("mid"))
        .otherwise(F.lit("high")),
    )
)

processed_dynamic_frame = DynamicFrame.fromDF(feature_df, glue_context, "processed_dynamic_frame")

glue_context.write_dynamic_frame.from_options(
    frame=processed_dynamic_frame,
    connection_type="s3",
    connection_options={"path": args["target_path"]},
    format="parquet",
)

job.commit()
