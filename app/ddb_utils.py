from .common import COMFYUI_LOG_PATH
import datetime
import os 
import boto3

node_table_name = "ComfyNode" + os.environ.get('DDB_TABLE_POSTFIX', "")
package_table_name = "ComfyNodePackage" + os.environ.get('DDB_TABLE_POSTFIX', "")
job_table_name = "Job" + os.environ.get('DDB_TABLE_POSTFIX', "")

try:
    dynamodb = boto3.resource(
        'dynamodb'
    )
    ddb_node_table = dynamodb.Table(node_table_name)
    ddb_package_table = dynamodb.Table(package_table_name)
    ddb_job_table = dynamodb.Table(job_table_name)
except Exception as e:
    print("❌❌ Error in ddb_utils",e)

#prompt job
def updateRunJob(item):
    try:
        id = item['id']  # Extract the primary key from the item
        
        # Prepare the UpdateExpression and ExpressionAttributeValues
        update_expression = "SET #updatedAt = :updatedAt"
        expression_attribute_values = {
            ':updatedAt': datetime.datetime.now().replace(microsecond=0).isoformat()
        }
        expression_attribute_names = {
            '#updatedAt': 'updatedAt'
        }
        
        # Dynamically add other fields to update (except the primary key 'id')
        for key, value in item.items():
            if key != 'id':  # Skip the id since it's used as the key
                placeholder = f"#{key}"
                update_expression += f", {placeholder} = :{key}"
                expression_attribute_values[f":{key}"] = value
                expression_attribute_names[placeholder] = key
        
        response = ddb_job_table.update_item(
            Key={'id': id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames=expression_attribute_names,  # Include this line
            ReturnValues='UPDATED_NEW'
        )
        return response
    except Exception as e:
        print("❌🔴Error updating job item in DynamoDB:", e)
        return None

def updateRunJobLogs(item):
    with open(COMFYUI_LOG_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
        print('🪵🪵log content', content)
        return updateRunJob({
            **item,
            'logs': content
        })

def finishJobWithError(id, error):
    return updateRunJob({
        'id': id,
        'error': error,
        'status': 'FAIL',
        "finishedAt": datetime.datetime.now().replace(microsecond=0).isoformat(),
    })