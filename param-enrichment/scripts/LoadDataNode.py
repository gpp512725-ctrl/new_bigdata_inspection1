#!/usr/bin/env python3
"""
Load and validate input data for param-enrichment skill.

This node loads the input JSON file, validates required fields,
and extracts actionBasics entries that match the user-specified action_names.
It also filters out manual actions (action_tag == "human") as they don't need parameter enrichment.
"""

import json
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_input_data(input_file: str) -> Dict[str, Any]:
    """
    Load input data from JSON file.
    
    Args:
        input_file: Path to input JSON file
        
    Returns:
        Dictionary containing loaded input data
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded input data from {input_file}")
        return data
    except Exception as e:
        logger.error(f"Failed to load input data from {input_file}: {e}")
        raise

def validate_required_fields(data: Dict[str, Any]) -> None:
    """
    Validate that required fields are present in input data.
    
    Args:
        data: Input data dictionary
        
    Raises:
        ValueError: If required fields are missing
    """
    required_fields = ['action_names', 'actionBasics', 'abnormalInstances', 'alertInfo']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise ValueError(f"Missing required fields in input data: {missing_fields}")

def filter_action_basics(action_basics: List[Dict], action_names: List[str]) -> List[Dict]:
    """
    Filter actionBasics entries that match user-specified action_names.
    
    Args:
        action_basics: List of action basics dictionaries
        action_names: List of action names to match
        
    Returns:
        Filtered list of action basics dictionaries
    """
    if not action_names:
        # If no action names specified, return all non-manual actions
        filtered = [action for action in action_basics if action.get('action_tag') != 'human']
        logger.info(f"No action names specified, returning {len(filtered)} non-manual actions")
        return filtered
    
    # Create a set for faster lookup
    action_names_set = set(action_names)
    
    # Filter actions that match the specified names and are not manual
    filtered = [
        action for action in action_basics 
        if action.get('action_des') in action_names_set and action.get('action_tag') != 'human'
    ]
    
    logger.info(f"Filtered {len(filtered)} actions matching {len(action_names)} specified names")
    return filtered

def enrich_action_basics_with_extra_info(action_basics: List[Dict], abnormal_instances: List[Dict]) -> List[Dict]:
    """
    Enrich actionBasics with extra_info containing instance_id and ip from abnormalInstances.
    
    Args:
        action_basics: List of action basics dictionaries
        abnormal_instances: List of abnormal instance dictionaries
        
    Returns:
        Enriched list of action basics dictionaries with extra_info
    """
    # Create a mapping from feature_code to instances for faster lookup
    feature_to_instances = {}
    for instance in abnormal_instances:
        feature_code = instance.get('feature_code')
        if feature_code:
            if feature_code not in feature_to_instances:
                feature_to_instances[feature_code] = []
            feature_to_instances[feature_code].append(instance)
    
    enriched_actions = []
    for action in action_basics:
        feature_code = action.get('feature_code')
        extra_info = {}
        
        if feature_code and feature_code in feature_to_instances:
            # Use the first matching instance for now (could be enhanced to handle multiple)
            instance = feature_to_instances[feature_code][0]
            extra_info = {
                'instance_id': instance.get('instance_id'),
                'ip': instance.get('ip')
            }
        
        # Create enriched action with extra_info
        enriched_action = action.copy()
        enriched_action['extra_info'] = extra_info
        enriched_actions.append(enriched_action)
    
    logger.info(f"Enriched {len(enriched_actions)} actions with extra_info")
    return enriched_actions

def main(input_file: str) -> List[Dict]:
    """
    Main function to load and process input data.
    
    Args:
        input_file: Path to input JSON file
        
    Returns:
        Processed list of action basics dictionaries ready for parameter filling
    """
    # Load input data
    data = load_input_data(input_file)
    
    # Validate required fields
    validate_required_fields(data)
    
    # Extract required fields
    action_names = data['action_names']
    action_basics = data['actionBasics']
    abnormal_instances = data['abnormalInstances']
    alert_info = data['alertInfo']
    
    # Log input summary
    logger.info(f"Input summary - Actions requested: {len(action_names)}, "
                f"Available actions: {len(action_basics)}, "
                f"Abnormal instances: {len(abnormal_instances)}")
    
    # Filter action basics based on action names and exclude manual actions
    filtered_actions = filter_action_basics(action_basics, action_names)
    
    # Enrich with extra_info
    enriched_actions = enrich_action_basics_with_extra_info(filtered_actions, abnormal_instances)
    
    return enriched_actions

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load and validate input data for param-enrichment skill")
    parser.add_argument("--input-file", required=True, help="Path to input JSON file")
    parser.add_argument("--output-file", required=True, help="Path to output JSON file")
    
    args = parser.parse_args()
    
    try:
        result = main(args.input_file)
        
        # Write result to output file
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully wrote processed data to {args.output_file}")
        
    except Exception as e:
        logger.error(f"Error in LoadDataNode: {e}")
        raise