import os
import logging
import pandas as pd

from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS
from pyspark.sql.functions import explode
import pyspark.sql.functions as func

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecommendationEngine:
    """A movie recommendation engine
    """
    def get_top_ratings(self, user_id, item_count):
        """Recommends top several item (total item is item_count) to a user"""
        users = self.ratingsdf.select(self.als.getUserCol())
        users = users.filter(users.user_id == user_id)
        userSubsetRecs = self.model.recommendForUserSubset(users, item_count)
        userSubsetRecs = userSubsetRecs.withColumn("recommendations", explode("recommendations"))
        userSubsetRecs = userSubsetRecs.select(func.col('recommendations')['item_id'].alias('item_id')).drop('recommendations')
        
        userSubsetRecs = userSubsetRecs.toPandas()
        userSubsetRecs = userSubsetRecs.to_json()
        return userSubsetRecs

    def get_top_item_recommend(self, item_id, user_count):
        """Recommends a item to top several user (total user is user_count)"""
        items = self.ratingsdf.select(self.als.getItemCol())
        items = items.filter(items.item_id == item_id)
        itemSubsetRecs = self.model.recommendForItemSubset(items, user_count)
        itemSubsetRecs = itemSubsetRecs.withColumn("recommendations", explode("recommendations"))
        itemSubsetRecs = itemSubsetRecs.select(func.col('recommendations')['user_id'].alias('user_id')).drop('recommendations')
       
        itemSubsetRecs = itemSubsetRecs.toPandas()
        itemSubsetRecs = itemSubsetRecs.to_json()
        return itemSubsetRecs

    def get_ratings_for_item_ids(self, user_id, item_id):
        """Given a user_id and a item_id, get ratings for them"""
        request = self.spark_session.createDataFrame([(user_id, item_id)], ["user_id", "item_id"])
        ratings = self.model.transform(request).collect()
        return ratings

    def __train_model(self):
        """Train the ALS model with the current dataset """
        logger.info("Training the ALS model...")
        self.als = ALS(maxIter=5, regParam=0.01, userCol="user_id", itemCol="item_id", ratingCol="rating",
                  coldStartStrategy="drop")
        self.model = self.als.fit(self.ratingsdf)
        logger.info("ALS model built!")

    
    def __init__(self, spark_session, dataset_path):
        """Init the recommendation engine given a Spark context and a dataset path
        """
        logger.info("Starting up the Recommendation Engine: ")
        self.spark_session = spark_session

        # Load ratings data for later use
        logger.info("Loading Ratings data...")
        ratings_file_path = os.path.join(dataset_path, 'renttherunway_final_data.json')
        self.ratingsdf = spark_session.read.json(ratings_file_path).na.drop()
        self.ratingsdf = self.ratingsdf.select(self.ratingsdf.user_id.cast("int"),self.ratingsdf.item_id.cast("int"),self.ratingsdf.rating.cast("int"))
        
        # Train the model
        self.__train_model()
