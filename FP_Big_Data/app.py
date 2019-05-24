from flask import Blueprint

main = Blueprint('main', __name__)

import json
from engine import RecommendationEngine

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from flask import Flask, request

@main.route("/<int:data_type>/<int:user_id>/recommendeditem/<int:item_count>", methods=["GET"])
def top_rating(data_type,user_id, item_count):
    logger.debug("User %s top item's rating requested", user_id)
    top_rated = recommendation_engine.get_top_ratings(data_type,user_id, item_count)
    return json.dumps(top_rated)


@main.route("/<int:data_type>/<int:item_id>/recommendeduser/<int:user_count>", methods=["GET"])
def top_item(data_type,item_id,user_count):
    logger.debug("Item %s top user recommending", item_id)
    top_rated = recommendation_engine.get_top_item_recommend(data_type,item_id, user_count)
    return json.dumps(top_rated)


@main.route("/<int:data_type>/<int:user_id>/getratings/<int:item_id>", methods=["GET"])
def item_rating(data_type,user_id, item_id):
    logger.debug("User %s rating requested for item %s", user_id, item_id)
    ratings = recommendation_engine.get_ratings_for_item_ids(data_type,user_id, item_id)
    return json.dumps(ratings)

def create_app(spark_session, dataset_path):
    global recommendation_engine
    recommendation_engine = RecommendationEngine(spark_session, dataset_path)
    app = Flask(__name__)
    app.register_blueprint(main)
    return app