"""
Prompt Preparation Functions for SmartBuild
Version: 3.0.0
Created: 2025-08-29
Updated: 2025-08-31 - MAJOR REFACTOR: Added common method for diagram ID extraction

CRITICAL: These functions prepare prompts AND save them to the correct location.
They return INSTRUCTIONS for Claude to read the prompt file, NOT the prompt content.
The job queue manager simply sends these instructions to Claude via tmux.

Each function returns a tuple: (instruction_text, prompt_save_path)
Where instruction_text is what gets sent to Claude (e.g., "Please read and process...")

Version 3.0.0 Changes:
- Added get_diagram_id_from_path() common method
- All functions now use the common method for consistent path extraction
- Fixed issue where names with underscores were being truncated
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

def get_diagram_id_from_path(diagram_path: Optional[str]) -> str:
    """
    Extract the diagram ID from a diagram file path.
    
    CRITICAL: This is the SINGLE SOURCE OF TRUTH for diagram ID extraction.
    All prompt preparation functions MUST use this method.
    
    Args:
        diagram_path: Path to the diagram file (e.g., "path/to/ecommerce_platform_architecture_cleanedup.xml")
        
    Returns:
        The diagram ID (filename without extension)
        
    Examples:
        "ecommerce_platform_architecture_cleanedup.xml" -> "ecommerce_platform_architecture_cleanedup"
        "architecture.drawio" -> "architecture"
        "my_awesome_project_final_v2.xml" -> "my_awesome_project_final_v2"
    """
    if not diagram_path:
        return "architecture"  # Default fallback
    
    # Use Path.stem to get filename without extension
    # This preserves the full filename including all underscores
    return Path(diagram_path).stem

def prepare_cost_analysis_prompt(
    session_id: str,
    run_id: str,
    metadata: Dict[str, Any]
) -> Tuple[str, Path]:
    """
    Prepare the cost analysis prompt.
    
    Args:
        session_id: The session ID
        run_id: The run ID
        metadata: Job metadata containing diagram_path, diagram_name, etc.
        
    Returns:
        Tuple of (instruction_text, prompt_save_path)
        Where instruction_text is what gets sent to Claude
    """
    # Extract metadata
    diagram_path = metadata.get('diagram_path')
    diagram_name = metadata.get('diagram_name', 'architecture')
    
    # Create prompt save path
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Use common method for diagram ID extraction
    diagram_id = get_diagram_id_from_path(diagram_path)
    
    # Try to use artifact-specific path if available
    if diagram_path:
        prompt_dir = Path(f"sessions/active/{session_id}/runs/{run_id}/artifacts/{diagram_id}/prompts")
        output_path = Path(f"sessions/active/{session_id}/runs/{run_id}/artifacts/{diagram_id}/cost_analysis")
    else:
        prompt_dir = Path(f"sessions/active/{session_id}/runs/{run_id}/prompts")
        output_path = Path(f"sessions/active/{session_id}/runs/{run_id}/cost_analysis")
    
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_save_path = prompt_dir / f"cost_analysis_{timestamp}.txt"
    
    # Load requirements
    req_file = Path(f"sessions/active/{session_id}/requirements.json")
    requirements = {}
    if req_file.exists():
        with open(req_file, 'r') as f:
            requirements = json.load(f)
    
    # Load architecture diagram XML
    architecture_xml = ""
    if diagram_path and Path(diagram_path).exists():
        with open(diagram_path, 'r', encoding='utf-8') as f:
            architecture_xml = f.read()
    
    # Load cost-analyzer agent prompt
    agent_file = Path(".claude/agents/cost-analyzer.md")
    agent_prompt = ""
    if agent_file.exists():
        with open(agent_file, 'r') as f:
            agent_prompt = f.read()
    
    # Build the full prompt
    full_prompt = f"""You are an AWS Cost Optimization Specialist. Your task is to analyze the provided AWS architecture and create a comprehensive cost analysis report.

{agent_prompt}

## Project Requirements:
```json
{json.dumps(requirements, indent=2)}
```

## Architecture Diagram (draw.io XML):
```xml
{architecture_xml}
```

## Your Task:
Please analyze this AWS architecture and provide TWO comprehensive cost calculations:

1. **BASELINE COSTS** - Calculate costs using standard on-demand pricing without any optimizations
2. **OPTIMIZED COSTS** - Calculate costs with all possible optimizations applied:
   - Reserved Instances (1-year and 3-year options)
   - Savings Plans
   - Spot Instances where applicable
   - Right-sizing recommendations
   - Storage tier optimizations

For EACH calculation, provide:
- Detailed breakdown by service
- Monthly and annual totals
- Assumptions made
- Confidence level in estimates

Then provide:
- Comparison table showing savings
- Optimization recommendations ranked by impact
- Implementation roadmap

## Output Format:
Create a comprehensive markdown document with:
1. Executive Summary
2. Baseline Cost Analysis (detailed)
3. Optimized Cost Analysis (detailed)
4. Savings Comparison
5. Optimization Strategies
6. Implementation Roadmap
7. Monitoring Recommendations

IMPORTANT: Save your analysis to: {output_path}/cost_analysis.md

Do NOT save files anywhere else. Create only the cost_analysis.md file in the specified directory.

When you have completed all tasks and saved all files, print "TASK COMPLETED" as the final line of your output.
"""
    
    # Save the prompt
    with open(prompt_save_path, 'w', encoding='utf-8') as f:
        f.write(full_prompt)
    
    # Create instruction for Claude to read the prompt file
    instruction = f"""Please read and process the prompt from this file:
{prompt_save_path}

CRITICAL: Save all outputs to: {output_path}/
Do not save any files outside of this directory."""
    
    return instruction, prompt_save_path


def prepare_technical_documentation_prompt(
    session_id: str,
    run_id: str,
    metadata: Dict[str, Any]
) -> Tuple[str, Path]:
    """
    Prepare the technical documentation generation prompt.
    
    Args:
        session_id: The session ID
        run_id: The run ID
        metadata: Job metadata containing diagram_path, docs_path, etc.
        
    Returns:
        Tuple of (instruction_text, prompt_save_path)
        Where instruction_text is what gets sent to Claude
    """
    # Extract metadata
    diagram_path = metadata.get('diagram_path')
    docs_path = metadata.get('docs_path', Path(f"sessions/active/{session_id}/runs/{run_id}/docs"))
    
    # Create prompt save path
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Use common method for diagram ID extraction
    diagram_id = get_diagram_id_from_path(diagram_path)
    
    # Try to use artifact-specific path if available
    if diagram_path:
        prompt_dir = Path(f"sessions/active/{session_id}/runs/{run_id}/artifacts/{diagram_id}/prompts")
        output_path = Path(f"sessions/active/{session_id}/runs/{run_id}/artifacts/{diagram_id}/docs")
    else:
        prompt_dir = Path(f"sessions/active/{session_id}/runs/{run_id}/prompts")
        output_path = Path(f"sessions/active/{session_id}/runs/{run_id}/docs")
    
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_save_path = prompt_dir / f"technical_documentation_{timestamp}.txt"
    
    # Load requirements
    req_file = Path(f"sessions/active/{session_id}/requirements.json")
    requirements = {}
    if req_file.exists():
        with open(req_file, 'r') as f:
            requirements = json.load(f)
    
    # Load architecture diagram XML
    architecture_xml = ""
    if diagram_path and Path(diagram_path).exists():
        with open(diagram_path, 'r', encoding='utf-8') as f:
            architecture_xml = f.read()
    
    # Build the full prompt
    full_prompt = f"""You are a Senior AWS Solutions Architect tasked with creating comprehensive technical documentation for an AWS architecture.

## Project Requirements:
```json
{json.dumps(requirements, indent=2)}
```

## Architecture Diagram (draw.io XML):
```xml
{architecture_xml}
```

## Your Task:
Create comprehensive technical documentation for this AWS architecture including:

1. **Architecture Overview**
   - High-level description of the solution
   - Key components and their purposes
   - Design principles followed

2. **Component Details**
   - Detailed description of each AWS service used
   - Configuration specifications
   - Integration points between components

3. **Security Architecture**
   - Security controls and best practices
   - IAM roles and policies
   - Network security (Security Groups, NACLs)
   - Data encryption (at rest and in transit)
   - Compliance considerations

4. **High Availability & Disaster Recovery**
   - Availability zones and regions
   - Backup strategies
   - Failover mechanisms
   - RTO/RPO objectives

5. **Performance & Scalability**
   - Performance optimization strategies
   - Auto-scaling configurations
   - Load balancing setup
   - Caching strategies

6. **Monitoring & Logging**
   - CloudWatch metrics and alarms
   - Logging strategy (CloudTrail, VPC Flow Logs, etc.)
   - Application monitoring
   - Cost monitoring

7. **Deployment & Operations**
   - Deployment procedures
   - CI/CD pipeline recommendations
   - Operational procedures
   - Maintenance windows

8. **Cost Optimization**
   - Cost-saving opportunities
   - Resource tagging strategy
   - Budget alerts

## Output Format:
Please provide the documentation in clear, structured markdown format with proper headings, tables where appropriate, and detailed explanations.

IMPORTANT: Save all output files to this directory ONLY:
{output_path}/

Create the following files:
- technical_documentation.md - Main technical documentation
- system_architecture.md - Detailed system architecture
- deployment_guide.md - Deployment procedures
- api_documentation.md - API specifications (if applicable)

Do NOT save files anywhere else. All outputs MUST be in the specified directory.

Begin creating the technical documentation:

When you have completed all tasks and saved all files, print "TASK COMPLETED" as the final line of your output.
"""
    
    # Save the prompt
    with open(prompt_save_path, 'w', encoding='utf-8') as f:
        f.write(full_prompt)
    
    # Create instruction for Claude to read the prompt file
    instruction = f"""Please read and process the prompt from this file:
{prompt_save_path}

CRITICAL: Save all outputs to: {output_path}/
Do not save any files outside of this directory."""
    
    return instruction, prompt_save_path


def prepare_terraform_prompt(
    session_id: str,
    run_id: str,
    metadata: Dict[str, Any]
) -> Tuple[str, Path]:
    """
    Prepare the Terraform code generation prompt.
    
    Args:
        session_id: The session ID
        run_id: The run ID
        metadata: Job metadata containing diagram_path, terraform_path, etc.
        
    Returns:
        Tuple of (instruction_text, prompt_save_path)
        Where instruction_text is what gets sent to Claude
    """
    # Extract metadata
    diagram_path = metadata.get('diagram_path')
    terraform_path = metadata.get('terraform_path', Path(f"sessions/active/{session_id}/runs/{run_id}/terraform"))
    
    # Create prompt save path
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Use common method for diagram ID extraction
    diagram_id = get_diagram_id_from_path(diagram_path)
    
    # Try to use artifact-specific path if available
    if diagram_path:
        prompt_dir = Path(f"sessions/active/{session_id}/runs/{run_id}/artifacts/{diagram_id}/prompts")
        output_path = Path(f"sessions/active/{session_id}/runs/{run_id}/artifacts/{diagram_id}/terraform")
    else:
        prompt_dir = Path(f"sessions/active/{session_id}/runs/{run_id}/prompts")
        output_path = Path(f"sessions/active/{session_id}/runs/{run_id}/terraform")
    
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_save_path = prompt_dir / f"terraform_{timestamp}.txt"
    
    # Load requirements
    req_file = Path(f"sessions/active/{session_id}/requirements.json")
    requirements = {}
    if req_file.exists():
        with open(req_file, 'r') as f:
            requirements = json.load(f)
    
    # Load architecture diagram XML
    architecture_xml = ""
    if diagram_path and Path(diagram_path).exists():
        with open(diagram_path, 'r', encoding='utf-8') as f:
            architecture_xml = f.read()
    
    # Load terraform-specialist agent prompt
    agent_file = Path(".claude/agents/terraform-specialist.md")
    agent_prompt = ""
    if agent_file.exists():
        with open(agent_file, 'r') as f:
            agent_prompt = f.read()
    
    # Build the full prompt
    full_prompt = f"""You are a Terraform Infrastructure Expert. Your task is to create production-ready Terraform code for the provided AWS architecture.

{agent_prompt}

## Project Requirements:
```json
{json.dumps(requirements, indent=2)}
```

## Architecture Diagram (draw.io XML):
```xml
{architecture_xml}
```

## Your Task:
Generate complete, production-ready Terraform code for this AWS architecture including:

1. **Module Structure**
   - Organized module hierarchy
   - Reusable components
   - Clear separation of concerns

2. **Resource Definitions**
   - All AWS resources from the architecture
   - Proper resource naming conventions
   - Resource dependencies and relationships

3. **Variables & Outputs**
   - Input variables with descriptions and defaults
   - Type constraints and validation
   - Meaningful outputs for resource attributes

4. **Security Best Practices**
   - IAM roles and policies using least privilege
   - Security groups with minimal required access
   - KMS encryption where applicable
   - Secrets management

5. **High Availability**
   - Multi-AZ deployments
   - Auto-scaling configurations
   - Load balancer setup

6. **State Management**
   - Remote state configuration
   - State locking
   - State file organization

7. **Environment Support**
   - Support for multiple environments (dev, staging, prod)
   - Environment-specific configurations
   - Variable files for each environment

## Output Format:
Create well-structured, commented Terraform files following HashiCorp best practices.

The code should be:
- Production-ready
- Modular and reusable
- Well-documented with inline comments
- Following Terraform naming conventions
- Include terraform.tfvars.example with sample values

Create a complete Terraform module structure with:
- main.tf - Main resource definitions
- variables.tf - Input variables
- outputs.tf - Output values
- providers.tf - Provider configuration
- terraform.tfvars.example - Example variable values
- README.md - Usage instructions

IMPORTANT: Save all output files to this directory ONLY:
{output_path}/

Create the following files:
- main.tf - Main resource definitions
- variables.tf - Input variables
- outputs.tf - Output values
- providers.tf - Provider configuration
- terraform.tfvars.example - Example variable values
- README.md - Usage instructions

Do NOT save files anywhere else. All outputs MUST be in the specified directory.

Begin generating the Terraform code:

When you have completed all tasks and saved all files, print "TASK COMPLETED" as the final line of your output.
"""
    
    # Save the prompt
    with open(prompt_save_path, 'w', encoding='utf-8') as f:
        f.write(full_prompt)
    
    # Create instruction for Claude to read the prompt file
    instruction = f"""Please read and process the prompt from this file:
{prompt_save_path}

CRITICAL: Save all outputs to: {output_path}/
Do not save any files outside of this directory."""
    
    return instruction, prompt_save_path


def prepare_cloudformation_prompt(
    session_id: str,
    run_id: str,
    metadata: Dict[str, Any]
) -> Tuple[str, Path]:
    """
    Prepare the CloudFormation template generation prompt.
    
    Args:
        session_id: The session ID
        run_id: The run ID
        metadata: Job metadata containing diagram_path, cf_path, etc.
        
    Returns:
        Tuple of (instruction_text, prompt_save_path)
        Where instruction_text is what gets sent to Claude
    """
    # Extract metadata
    diagram_path = metadata.get('diagram_path')
    cf_path = metadata.get('cf_path', Path(f"sessions/active/{session_id}/runs/{run_id}/cloudformation"))
    
    # Create prompt save path
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Use common method for diagram ID extraction
    diagram_id = get_diagram_id_from_path(diagram_path)
    
    # Try to use artifact-specific path if available
    if diagram_path:
        prompt_dir = Path(f"sessions/active/{session_id}/runs/{run_id}/artifacts/{diagram_id}/prompts")
        output_path = Path(f"sessions/active/{session_id}/runs/{run_id}/artifacts/{diagram_id}/cloudformation")
    else:
        prompt_dir = Path(f"sessions/active/{session_id}/runs/{run_id}/prompts")
        output_path = Path(f"sessions/active/{session_id}/runs/{run_id}/cloudformation")
    
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_save_path = prompt_dir / f"cloudformation_{timestamp}.txt"
    
    # Load requirements
    req_file = Path(f"sessions/active/{session_id}/requirements.json")
    requirements = {}
    if req_file.exists():
        with open(req_file, 'r') as f:
            requirements = json.load(f)
    
    # Load architecture diagram XML
    architecture_xml = ""
    if diagram_path and Path(diagram_path).exists():
        with open(diagram_path, 'r', encoding='utf-8') as f:
            architecture_xml = f.read()
    
    # Load cloudformation-expert agent prompt
    agent_file = Path(".claude/agents/cloudformation-expert.md")
    agent_prompt = ""
    if agent_file.exists():
        with open(agent_file, 'r') as f:
            agent_prompt = f.read()
    
    # Build the full prompt
    full_prompt = f"""You are a CloudFormation Infrastructure Expert. Your task is to create production-ready CloudFormation templates for the provided AWS architecture.

{agent_prompt}

## Project Requirements:
```json
{json.dumps(requirements, indent=2)}
```

## Architecture Diagram (draw.io XML):
```xml
{architecture_xml}
```

## Your Task:
Generate complete, production-ready CloudFormation templates for this AWS architecture including:

1. **Template Structure**
   - Nested stacks for complex architectures
   - Modular template design
   - Cross-stack references

2. **Parameters**
   - Input parameters with descriptions
   - Allowed values and constraints
   - Default values where appropriate
   - Parameter groups for organization

3. **Resources**
   - All AWS resources from the architecture
   - Proper resource dependencies
   - Deletion policies
   - Update policies

4. **Mappings & Conditions**
   - Region-specific mappings
   - Environment-based conditions
   - AMI mappings

5. **Security**
   - IAM roles and policies
   - Security groups
   - KMS keys
   - Secrets Manager integration

6. **Outputs**
   - Export values for cross-stack references
   - Important resource attributes
   - Connection strings and endpoints

7. **Best Practices**
   - Use of AWS::Include for reusable components
   - Metadata for CloudFormation Designer
   - Stack policies
   - Change sets support

## Output Format:
Create well-structured CloudFormation templates in YAML format with:
- Clear comments explaining each section
- Proper indentation and formatting
- Parameter descriptions
- Resource tags for cost tracking

The templates should be:
- Production-ready
- Modular and reusable
- Well-documented
- Following AWS CloudFormation best practices
- Include parameter files for different environments

IMPORTANT: Save all output files to this directory ONLY:
{output_path}/

Create the following files:
- main-stack.yaml - Main CloudFormation template
- parameters-dev.json - Development environment parameters
- parameters-prod.json - Production environment parameters
- README.md - Deployment instructions

If the architecture is complex, also create:
- network-stack.yaml - VPC and networking resources
- compute-stack.yaml - EC2, Lambda, ECS resources
- database-stack.yaml - RDS, DynamoDB resources
- storage-stack.yaml - S3, EFS resources

Do NOT save files anywhere else. All outputs MUST be in the specified directory.

Begin creating the CloudFormation templates:

When you have completed all tasks and saved all files, print "TASK COMPLETED" as the final line of your output.
"""
    
    # Save the prompt
    with open(prompt_save_path, 'w', encoding='utf-8') as f:
        f.write(full_prompt)
    
    # Create instruction for Claude to read the prompt file
    instruction = f"""Please read and process the prompt from this file:
{prompt_save_path}

CRITICAL: Save all outputs to: {output_path}/
Do not save any files outside of this directory."""
    
    return instruction, prompt_save_path


def prepare_requirements_prompt(
    session_id: str,
    user_input: str,
    uploaded_files: list = None
) -> Tuple[str, Path]:
    """
    Prepare the requirements extraction prompt.
    
    Args:
        session_id: The session ID
        user_input: The user's project description
        uploaded_files: List of uploaded file paths
        
    Returns:
        Tuple of (instruction_text, prompt_save_path)
        Where instruction_text is what gets sent to Claude
    """
    # Create prompt save path
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    prompt_dir = Path(f"sessions/active/{session_id}/prompts")
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_save_path = prompt_dir / f"requirements_extraction_{timestamp}.txt"
    
    # Build the full prompt
    file_section = ""
    if uploaded_files:
        file_section = "\n## Uploaded Files:\n"
        for file_path in uploaded_files:
            file_section += f"- {file_path}\n"
    
    full_prompt = f"""You are an expert AWS Solutions Architect. Extract and structure the requirements from the following project description.

## User's Project Description:
{user_input}
{file_section}

## Your Task:
Analyze the project description and extract structured requirements. Create a comprehensive requirements document in JSON format that includes:

1. **Project Overview**
   - Name
   - Description
   - Primary objectives
   - Success criteria

2. **Functional Requirements**
   - Core features
   - User stories
   - API requirements
   - Integration points

3. **Non-Functional Requirements**
   - Performance targets
   - Scalability needs
   - Security requirements
   - Compliance needs
   - Availability targets (SLA)

4. **Technical Constraints**
   - Technology preferences
   - Budget constraints
   - Timeline
   - Team expertise

5. **AWS Services Recommendations**
   - Recommended services based on requirements
   - Justification for each service
   - Alternative options

## Output Format:
Create a structured JSON document with all extracted requirements.

IMPORTANT: Save the requirements to: sessions/active/{session_id}/requirements.json

The JSON should follow this structure:
```json
{{
  "project": {{
    "name": "Project Name",
    "description": "Brief description",
    "objectives": ["objective1", "objective2"],
    "success_criteria": ["criteria1", "criteria2"]
  }},
  "functional_requirements": {{
    "features": ["feature1", "feature2"],
    "user_stories": ["story1", "story2"],
    "apis": ["api1", "api2"],
    "integrations": ["integration1", "integration2"]
  }},
  "non_functional_requirements": {{
    "performance": "Performance requirements",
    "scalability": "Scalability requirements",
    "security": "Security requirements",
    "compliance": ["compliance1", "compliance2"],
    "availability": "99.9% uptime"
  }},
  "technical_constraints": {{
    "technologies": ["tech1", "tech2"],
    "budget": "Budget information",
    "timeline": "Timeline information",
    "team_expertise": ["skill1", "skill2"]
  }},
  "aws_services": {{
    "recommended": [
      {{
        "service": "Service Name",
        "purpose": "Why this service",
        "alternatives": ["alt1", "alt2"]
      }}
    ]
  }}
}}
```

Begin extracting the requirements:

When you have completed all tasks and saved all files, print "TASK COMPLETED" as the final line of your output.
"""
    
    # Save the prompt
    with open(prompt_save_path, 'w', encoding='utf-8') as f:
        f.write(full_prompt)
    
    # Create instruction for Claude to read the prompt file
    instruction = f"""Please read and process the prompt from this file:
{prompt_save_path}

CRITICAL: Save the requirements to: sessions/active/{session_id}/requirements.json
Do not save files anywhere else."""
    
    return instruction, prompt_save_path


def prepare_solution_prompt(
    session_id: str,
    run_id: str,
    requirements: Dict[str, Any]
) -> Tuple[str, Path]:
    """
    Prepare the solution generation prompt.
    
    Args:
        session_id: The session ID
        run_id: The run ID
        requirements: The extracted requirements dictionary
        
    Returns:
        Tuple of (instruction_text, prompt_save_path)
        Where instruction_text is what gets sent to Claude
    """
    # Create prompt save path
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    prompt_dir = Path(f"sessions/active/{session_id}/runs/{run_id}/prompts")
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_save_path = prompt_dir / f"solution_generation_{timestamp}.txt"
    
    # Load solution-designer agent prompt
    agent_file = Path(".claude/agents/solution-designer.md")
    agent_prompt = ""
    if agent_file.exists():
        with open(agent_file, 'r') as f:
            agent_prompt = f.read()
    
    # Build the full prompt
    full_prompt = f"""You are a Master AWS Solutions Architect. Design a comprehensive AWS architecture solution based on the provided requirements.

{agent_prompt}

## Project Requirements:
```json
{json.dumps(requirements, indent=2)}
```

## Your Task:
Design and create a complete AWS architecture solution that:

1. **Addresses all functional requirements**
   - Implements all requested features
   - Supports all user stories
   - Provides required APIs
   - Enables necessary integrations

2. **Meets non-functional requirements**
   - Achieves performance targets
   - Scales to meet demand
   - Implements security best practices
   - Ensures compliance
   - Delivers required availability

3. **Works within constraints**
   - Uses recommended technologies
   - Stays within budget guidelines
   - Meets timeline requirements
   - Matches team expertise

4. **Follows AWS best practices**
   - Well-Architected Framework principles
   - Security by design
   - Cost optimization
   - Operational excellence

## Deliverables:

1. **Architecture Diagram**
   - Create a detailed draw.io XML diagram
   - Include all AWS services
   - Show data flows and connections
   - Add proper labels and descriptions
   - Save to: sessions/active/{session_id}/runs/{run_id}/diagrams/

2. **Solution Summary**
   - Executive overview
   - Key design decisions
   - Technology choices justification
   - Cost estimates
   - Risk assessment
   - Save to: sessions/active/{session_id}/runs/{run_id}/solution_summary.md

3. **Implementation Roadmap**
   - Phased implementation plan
   - Dependencies
   - Timeline
   - Resource requirements
   - Save to: sessions/active/{session_id}/runs/{run_id}/implementation_roadmap.md

Begin designing the solution:

When you have completed all tasks and saved all files, print "TASK COMPLETED" as the final line of your output.
"""
    
    # Save the prompt
    with open(prompt_save_path, 'w', encoding='utf-8') as f:
        f.write(full_prompt)
    
    # Create instruction for Claude to read the prompt file
    instruction = f"""Please read and process the prompt from this file:
{prompt_save_path}

CRITICAL: Save all outputs to the specified directories under:
sessions/active/{session_id}/runs/{run_id}/

Do not save files anywhere else."""
    
    return instruction, prompt_save_path