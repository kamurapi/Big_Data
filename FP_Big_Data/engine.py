import os
import logging
import pandas as pd

from pyspark.ml.feature import IndexToString, StringIndexer
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS
from pyspark.sql.functions import explode
import pyspark.sql.functions as func

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecommendationEngine:
    """A movie recommendation engine
    """
    def get_top_ratings(self, UserId, item_count):
        """Recommends top several item (total item is item_count) to a user"""
        users = self.ratingsdf.select(self.als.getUserCol())
        users = users.filter(users.UserId == UserId)
        userSubsetRecs = self.model.recommendForUserSubset(users, item_count)
        userSubsetRecs = userSubsetRecs.withColumn("recommendations", explode("recommendations"))
        userSubsetRecs = userSubsetRecs.select(func.col('recommendations')['GameId'].alias('GameId')).drop('recommendations')
        
        userSubsetRecs = userSubsetRecs.toPandas()
        userSubsetRecs = userSubsetRecs.to_json()
        return userSubsetRecs

    def get_top_item_recommend(self, GameId, user_count):
        """Recommends a item to top several user (total user is user_count)"""
        items = self.ratingsdf.select(self.als.getItemCol())
        items = items.filter(items.GameId == GameId)
        itemSubsetRecs = self.model.recommendForItemSubset(items, user_count)
        itemSubsetRecs = itemSubsetRecs.withColumn("recommendations", explode("recommendations"))
        itemSubsetRecs = itemSubsetRecs.select(func.col('recommendations')['UserId'].alias('UserId')).drop('recommendations')
       
        itemSubsetRecs = itemSubsetRecs.toPandas()
        itemSubsetRecs = itemSubsetRecs.to_json()
        return itemSubsetRecs

    def get_ratings_for_item_ids(self, UserId, GameId):
        """Given a user_id and a item_id, get ratings for them"""
        request = self.spark_session.createDataFrame([(UserId, GameId)], ["UserId", "GameId"])
        ratings = self.model.transform(request).collect()
        return ratings

    def __train_model(self):
        """Train the ALS model with the current dataset """
        logger.info("Training the ALS model...")
        self.als = ALS(maxIter=5, regParam=0.01, userCol="UserId", itemCol="GameId", ratingCol="Userscore",
                  coldStartStrategy="drop")
        self.model = self.als.fit(self.ratingsdf)
        logger.info("ALS model built!")

    
    def __init__(self, spark_session, dataset_folder_path):
        """Init the recommendation engine given a Spark context and a dataset path
        """
        self.df = [None for i in range(10)]

        logger.info("Starting up the Recommendation Engine: ")
        self.spark_session = spark_session

        # Load ratings data for later use
        logger.info("Loading Ratings data...")
        file_index = 0
        while True:
            filename = 'result' + str(file_index) + '.txt'
            dataset_file_path = os.path.join(dataset_folder_path,filename)
            exist_file = os.path.isfile(dataset_file_path)

            if exist_file:
                logger.info(file_index)
                self.df[file_index] = spark_session.read.csv(dataset_file_path,header=None, inferSchema=True)
                self.df[file_index] = self.df[file_index].selectExpr("_c1 as Title" , "_c3 as Userscore", "_c5 as Username")
                self.df[file_index] = self.df[file_index].select(self.df[file_index].Username,self.df[file_index].Title,self.df[file_index].Userscore)

                logger.info("can load data")

                stringindexer = StringIndexer(inputCol='Username',outputCol='UserId')
                stringindexer.setHandleInvalid("keep")
                model = stringindexer.fit(self.df[file_index])
                indexed = model.transform(self.df[file_index]) 

                stringindexer_item = StringIndexer(inputCol='Title',outputCol='GameId')
                stringindexer_item.setHandleInvalid("keep") 
                model = stringindexer_item.fit(indexed)
                indexed = model.transform(indexed)

                logger.info("sucess conver")

                self.df[file_index] = indexed.select(indexed.Username,indexed.UserId,indexed.Title,indexed.GameId,indexed.Userscore.cast("int"))
                logger.info("get data frame")

                file_index+=1
            else:
                break

        self.ratingsdf =self.df[0]
        self.ratingsdf.show()
        # Train the model
        self.__train_model()
