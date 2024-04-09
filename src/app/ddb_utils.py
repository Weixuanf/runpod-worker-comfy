from githubUtils import download_and_upload_to_s3, get_github_repo_stars
import datetime
import os 
import boto3
import json

node_table_name = "ComfyNode" + os.environ.get('DDB_TABLE_POSTFIX', "")
package_table_name = "ComfyNodePackage" + os.environ.get('DDB_TABLE_POSTFIX', "")

try:
    dynamodb = boto3.resource(
        'dynamodb'
    )
    ddb_node_table = dynamodb.Table(node_table_name)
    ddb_package_table = dynamodb.Table(package_table_name)
except Exception as e:
    print("❌❌ Error in ddb_utils",e)

#####v2######
def put_node_package_ddb(item):
    try:
        repo_data = get_github_repo_stars(item.get('gitHtmlUrl'))
        owner_avatar_url= repo_data['owner_avatar_url'] if 'owner_avatar_url' in repo_data else None
        star_count = repo_data['stars'] if 'stars' in repo_data else None
        
        webDir = item.get('webDir')
        jsFilePaths = None
        if webDir:
            jsFilePaths = json.dumps(download_and_upload_to_s3(item['gitRepo'], webDir))
        response = ddb_package_table.put_item(Item={
            **item,
            'updatedAt': datetime.datetime.now().replace(microsecond=0).isoformat(),
            'totalStars': star_count,
            'ownerGitAvatarUrl': owner_avatar_url,
            'description': repo_data.get('description',''),
            'jsFilePaths': jsFilePaths
        })
        return item
    except Exception as e:
        print("❌🔴Error adding package item to DynamoDB:", e)
        return None

def put_node_ddb(item):
    # make sure to only create new node if it doesn't exist, to avoid override folderPaths field!
    try:
        response = ddb_node_table.put_item(
            Item={
                **item,
                'updatedAt': datetime.datetime.now().replace(microsecond=0).isoformat(),
            },
            ConditionExpression="attribute_not_exists(id)"
        )
        return item
    except Exception as e:
        print("🚼Error adding node item to DynamoDB:", e)
        return None