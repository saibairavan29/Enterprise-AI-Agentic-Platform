import logging
from edqi.models import EnterpriseDatasetProfile

logger = logging.getLogger(__name__)

class ProfileRepository:
    """
    Data access repository managing database operations for EnterpriseDatasetProfile models.
    """
    def save_profile(self, profile: EnterpriseDatasetProfile) -> EnterpriseDatasetProfile:
        """
        Saves or updates a dataset profile.
        """
        profile.save()
        return profile

    def get_profile_by_document_id(self, document_id: int) -> EnterpriseDatasetProfile:
        """
        Retrieves the profile associated with a given KnowledgeDocument ID.
        """
        return EnterpriseDatasetProfile.objects.filter(knowledge_document_id=document_id).order_by("-id").first()

    def delete_profiles_for_document(self, document_id: int):
        """
        Removes all profiles associated with a KnowledgeDocument ID.
        """
        EnterpriseDatasetProfile.objects.filter(knowledge_document_id=document_id).delete()
