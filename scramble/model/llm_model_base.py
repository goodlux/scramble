class LLMModelBase(ModelBase):
    """Base class for all Language Learning Models"""
    
    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        pass
    
    @abstractmethod
    def validate_response(self, response: str) -> bool:
        """Validate the response from the model"""
        pass