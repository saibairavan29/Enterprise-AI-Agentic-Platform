from django.urls import path
from policy_simulator.views import PolicySimulationEndpoint, PolicyConfigEndpoint, PolicyAssistantEndpoint

urlpatterns = [
    path('simulate/', PolicySimulationEndpoint.as_view(), name='policy_simulate'),
    path('config/', PolicyConfigEndpoint.as_view(), name='policy_config'),
    path('assistant/', PolicyAssistantEndpoint.as_view(), name='policy_assistant'),
]
