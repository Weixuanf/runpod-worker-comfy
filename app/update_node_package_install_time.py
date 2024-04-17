import boto3
import os

node_table_name = "ComfyNode" + os.environ.get('DDB_TABLE_POSTFIX', "")
package_table_name = "ComfyNodePackage" + os.environ.get('DDB_TABLE_POSTFIX', "")

try:
    dynamodb = boto3.resource(
        'dynamodb'
    )
    ddb_node_table = dynamodb.Table(node_table_name)
    ddb_package_table = dynamodb.Table(package_table_name)
except Exception as e:
    print("❌❌ Error in update_node_pacakge",e)
    
def update_node_package_install_time(gitUrl:str, install_time:float, restart_success:bool, restart_error: str):
    if gitUrl.endswith('.git'):
        gitUrl = gitUrl[:-4]
    if gitUrl.endswith('/'):
        gitUrl = gitUrl[:-1]
    repo = gitUrl.split('/')[-1]
    username = gitUrl.split('/')[-2]
    packageID = username + '_' + repo
    try:
        response = ddb_package_table.update_item(
            Key={
                'id': packageID
            },
            UpdateExpression="set installTime = :i, restartSuccess = :r, restartError = :e",
            ExpressionAttributeValues={
                ':i': str(install_time),
                ':r': restart_success,
                ':e': restart_error if len(restart_error) > 0 else None
            },
            ReturnValues="UPDATED_NEW"
        )
    except Exception as e:
        print("❌❌ Error in update_node_pacakge",e)
