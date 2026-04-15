# authnticate using gcloud
create pycharm project
pip install google-adk
adk create my_fourth_agent
set PROJECT_ID=trusty-solution-405810
set LOCATION_ID=us-central1

Deploy failed: [WinError 2] The system cannot find the file specified
if you face such error open new cmd and try again 

set PROJECT_ID=trusty-solution-405810
set LOCATION_ID=us-central1
adk deploy agent_engine  --project=$PROJECT_ID  --region=$LOCATION_ID --display_name="My fourth Agent"  my_fourth_agent
