from flask import Blueprint, jsonify, request
from .core import converter, utils
from pathlib import Path

api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

@api_blueprint.route('/files', methods=['GET'])
def get_files():
    """Returns a JSON structure of the download and convert directories."""
    download_tree = utils.get_file_structure(utils.DOWNLOAD_DIR_BASE)
    convert_tree = utils.get_file_structure(utils.CONVERT_DIR_BASE)
    return jsonify({
        "downloads": download_tree,
        "converted": convert_tree
    })

@api_blueprint.route('/convert', methods=['POST'])
def convert_file():
    data = request.get_json()
    file_path = data.get('file_path')
    target_format = data.get('target_format')
    output_type = data.get('output_type')

    if not all([file_path, target_format, output_type]):
        return jsonify({"error": "Missing required parameters"}), 400

    task_id = converter.handle_conversion(file_path, target_format, output_type)
    return jsonify({"task_id": task_id})