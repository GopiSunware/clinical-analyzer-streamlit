import os
import openai
import google.generativeai as genai
from typing import Dict, List, Any, Optional, Union
import json
import base64
from PIL import Image
import io

class UnifiedAIClient:
    """Unified client for both OpenAI and Google Gemini AI services"""
    
    def __init__(self, provider: str = "openai", **kwargs):
        """
        Initialize the AI client
        
        Args:
            provider: "openai" or "gemini"
            **kwargs: Provider-specific configuration
        """
        self.provider = provider.lower()
        self.model = kwargs.get('model', '')
        self.temperature = kwargs.get('temperature', 0.3)
        self.max_tokens = kwargs.get('max_tokens', 2000)
        
        if self.provider == "openai":
            self._init_openai(**kwargs)
        elif self.provider == "gemini":
            self._init_gemini(**kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _init_openai(self, **kwargs):
        """Initialize OpenAI client"""
        api_key = kwargs.get('api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        try:
            self.client = openai.OpenAI(api_key=api_key)
            self.legacy_client = False
        except Exception as e:
            print(f"Warning: Using legacy OpenAI client: {e}")
            openai.api_key = api_key
            self.client = None
            self.legacy_client = True
    
    def _init_gemini(self, **kwargs):
        """Initialize Gemini client using direct Google Generative AI API"""
        # Get API key from environment or kwargs
        api_key = kwargs.get('api_key') or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Set default model if not specified
        if not self.model:
            self.model = "gemini-1.5-flash"
        
        # Initialize the model
        self.client = genai.GenerativeModel(self.model)
        self.api_key = api_key
    
    def generate_text(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Generate text response from messages
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters
        
        Returns:
            Standardized response dict
        """
        if self.provider == "openai":
            return self._generate_openai(messages, **kwargs)
        elif self.provider == "gemini":
            return self._generate_gemini(messages, **kwargs)
    
    def _generate_openai(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate response using OpenAI"""
        try:
            # Override settings if provided
            temperature = kwargs.get('temperature', self.temperature)
            max_tokens = kwargs.get('max_tokens', self.max_tokens)
            model = kwargs.get('model', self.model)
            
            if self.client and not self.legacy_client:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                return {
                    'content': response.choices[0].message.content,
                    'model': response.model,
                    'usage': {
                        'prompt_tokens': response.usage.prompt_tokens if response.usage else None,
                        'completion_tokens': response.usage.completion_tokens if response.usage else None,
                        'total_tokens': response.usage.total_tokens if response.usage else None,
                    },
                    'finish_reason': response.choices[0].finish_reason
                }
            else:
                # Legacy client
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                return {
                    'content': response['choices'][0]['message']['content'],
                    'model': response.get('model', model),
                    'usage': response.get('usage', {}),
                    'finish_reason': response['choices'][0].get('finish_reason')
                }
                
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def _generate_gemini(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Generate response using direct Gemini API"""
        try:
            # Convert OpenAI message format to Gemini format
            gemini_prompt = self._convert_messages_to_gemini(messages)
            
            # Set generation config
            generation_config = genai.GenerationConfig(
                temperature=kwargs.get('temperature', self.temperature),
                max_output_tokens=kwargs.get('max_tokens', self.max_tokens),
            )
            
            # Generate response
            response = self.client.generate_content(
                gemini_prompt,
                generation_config=generation_config
            )
            
            return {
                'content': response.text,
                'model': self.model,
                'usage': {
                    'prompt_tokens': getattr(response.usage_metadata, 'prompt_token_count', None) if hasattr(response, 'usage_metadata') else None,
                    'completion_tokens': getattr(response.usage_metadata, 'candidates_token_count', None) if hasattr(response, 'usage_metadata') else None,
                    'total_tokens': getattr(response.usage_metadata, 'total_token_count', None) if hasattr(response, 'usage_metadata') else None,
                },
                'finish_reason': response.candidates[0].finish_reason.name if response.candidates else None
            }
            
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    def _convert_messages_to_gemini(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI messages format to Gemini format"""
        gemini_prompt = ""
        
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            
            if role == 'system':
                gemini_prompt += f"Instructions: {content}\n\n"
            elif role == 'user':
                gemini_prompt += f"User: {content}\n\n"
            elif role == 'assistant':
                gemini_prompt += f"Assistant: {content}\n\n"
        
        return gemini_prompt.strip()
    
    def analyze_image(self, image_path: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Analyze an image with AI
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt for analysis
            **kwargs: Additional parameters
        
        Returns:
            Standardized response dict
        """
        if self.provider == "openai":
            return self._analyze_image_openai(image_path, prompt, **kwargs)
        elif self.provider == "gemini":
            return self._analyze_image_gemini(image_path, prompt, **kwargs)
    
    def _analyze_image_openai(self, image_path: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Analyze image using OpenAI Vision"""
        try:
            # Check if model supports vision
            vision_model = kwargs.get('model', 'gpt-4o')
            if 'gpt-4' not in vision_model and 'gpt-4o' not in vision_model:
                raise ValueError(f"Model {vision_model} does not support vision")
            
            # Read and encode image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ]
            
            if self.client and not self.legacy_client:
                response = self.client.chat.completions.create(
                    model=vision_model,
                    messages=messages,
                    max_tokens=kwargs.get('max_tokens', 1500),
                    temperature=kwargs.get('temperature', 0.1)
                )
                
                return {
                    'content': response.choices[0].message.content,
                    'model': response.model,
                    'usage': {
                        'prompt_tokens': response.usage.prompt_tokens if response.usage else None,
                        'completion_tokens': response.usage.completion_tokens if response.usage else None,
                        'total_tokens': response.usage.total_tokens if response.usage else None,
                    }
                }
            else:
                raise ValueError("Legacy OpenAI client does not support vision")
                
        except Exception as e:
            raise Exception(f"OpenAI Vision error: {str(e)}")
    
    def _analyze_image_gemini(self, image_path: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Analyze image using Gemini Vision via direct API"""
        try:
            # Read and process the image
            image = Image.open(image_path)
            
            # Set generation config
            generation_config = genai.GenerationConfig(
                temperature=kwargs.get('temperature', 0.1),
                max_output_tokens=kwargs.get('max_tokens', 1500),
            )
            
            # Generate response with both text and image
            response = self.client.generate_content(
                [prompt, image],
                generation_config=generation_config
            )
            
            return {
                'content': response.text,
                'model': self.model,
                'usage': {
                    'prompt_tokens': getattr(response.usage_metadata, 'prompt_token_count', None) if hasattr(response, 'usage_metadata') else None,
                    'completion_tokens': getattr(response.usage_metadata, 'candidates_token_count', None) if hasattr(response, 'usage_metadata') else None,
                    'total_tokens': getattr(response.usage_metadata, 'total_token_count', None) if hasattr(response, 'usage_metadata') else None,
                }
            }
            
        except Exception as e:
            raise Exception(f"Gemini Vision error: {str(e)}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available models for the current provider"""
        if self.provider == "openai":
            return ["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4-turbo"]
        elif self.provider == "gemini":
            return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-1.5-flash-001", "gemini-1.5-pro-001"]
        return []
    
    def supports_vision(self) -> bool:
        """Check if current configuration supports image analysis"""
        if self.provider == "openai":
            return 'gpt-4' in self.model or 'gpt-4o' in self.model
        elif self.provider == "gemini":
            return True  # Most Gemini models support vision
        return False 