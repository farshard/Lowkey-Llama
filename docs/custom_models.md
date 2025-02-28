# Custom Model Guide

This guide explains how to create, customize, and optimize models for Lowkey Llama. Custom models allow you to tailor the behavior of language models to specific needs, such as improved verbosity, specialized knowledge domains, or different response characteristics.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Creating a Basic Custom Model](#creating-a-basic-custom-model)
3. [Model Optimization Techniques](#model-optimization-techniques)
4. [Advanced Configuration](#advanced-configuration)
5. [Testing and Validation](#testing-and-validation)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

Before creating custom models, ensure you have:
- Ollama installed and running
- Lowkey Llama set up
- Basic understanding of LLM parameters (temperature, top_p, etc.)

## Creating a Basic Custom Model

### Step 1: Create a Modelfile

Create a `.modelfile` file in the `models/` directory with the following format:

```
FROM base-model-name

# Parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 8192
PARAMETER num_predict 4096
PARAMETER repeat_penalty 1.1
PARAMETER seed 42

# Template for formatting inputs and outputs
TEMPLATE """
<s>{{if .System}}[INST] {{.System}} [/INST]</s>
{{end}}
<s>[INST] {{.Prompt}} [/INST]
{{.Response}}</s>
"""

# System message that provides context and instructions
SYSTEM """You are a helpful, knowledgeable assistant..."""
```

Replace `base-model-name` with a model like `mistral`, `llama2`, or `codellama`.

### Step 2: Build the Model

Open a terminal and run:

```bash
ollama create my-custom-model -f models/my-custom-model.modelfile
```

### Step 3: Add to Configuration

Add your model to `config.json`:

```json
"models": {
    "my-custom-model": {
        "temp": 0.7,
        "max_tokens": 4096,
        "context_window": 8192
    }
}
```

## Model Optimization Techniques

### Improving Response Completeness

If your model gives truncated responses:

```
# Enhanced parameters for more detailed responses
PARAMETER temperature 0.7
PARAMETER top_p 0.95
PARAMETER top_k 60
PARAMETER num_ctx 8192
PARAMETER num_predict 4096
PARAMETER repeat_penalty 1.18
PARAMETER repeat_last_n 64

SYSTEM """You are a helpful assistant specialized in providing comprehensive answers.

IMPORTANT INSTRUCTIONS:
1. ALWAYS provide detailed, complete responses with MULTIPLE PARAGRAPHS
2. Use examples and elaboration in your answers
3. Fully explain concepts with thorough descriptions
4. NEVER provide one-word or very short responses
5. Your answers should be at least 3-5 sentences minimum
6. If asked a question, always provide context and background information
7. Always finish your thoughts completely - never end mid-explanation

The quality of your response is measured by its completeness and detail."""
```

### Optimizing for Code Generation

For code-focused models:

```
# Parameters optimized for code generation
PARAMETER temperature 0.5
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 16384
PARAMETER num_predict 8192
PARAMETER repeat_penalty 1.05

SYSTEM """You are an expert software developer specialized in writing clean, efficient, and well-documented code.

When writing code:
1. Include detailed comments explaining complex logic
2. Follow best practices and design patterns
3. Consider edge cases and error handling
4. Ensure variable names are descriptive
5. Optimize for readability and maintainability

Always test your code mentally before providing it, and ensure it's complete and ready to run."""
```

### Optimizing for Creative Writing

For more creative responses:

```
# Parameters for creative content
PARAMETER temperature 0.85
PARAMETER top_p 0.92
PARAMETER top_k 70
PARAMETER num_ctx 8192
PARAMETER num_predict 4096
PARAMETER repeat_penalty 1.08

SYSTEM """You are a creative writer with exceptional storytelling skills.

When crafting content:
1. Use vivid imagery and descriptive language
2. Develop compelling narratives with clear structure
3. Create distinct character voices and perspectives
4. Balance dialogue and description
5. Maintain consistent tone and style

Your writing should be engaging, original, and evocative of emotion."""
```

## Advanced Configuration

### Parameter Optimization Guide

| Parameter | Description | Range | Use Case |
|-----------|-------------|-------|----------|
| temperature | Controls randomness | 0.0-1.0 | Higher: more creative, Lower: more deterministic |
| top_p | Nucleus sampling threshold | 0.0-1.0 | Higher: more diverse, Lower: more focused |
| top_k | Number of tokens to consider | 1-100 | Higher: more possibilities, Lower: more predictable |
| repeat_penalty | Penalty for repeating tokens | 1.0-2.0 | Higher: less repetition, Lower: more natural flow |
| num_ctx | Context window size | 2048-32768 | Higher: more context, but more resources |
| num_predict | Maximum tokens to generate | 128-32768 | Higher: longer responses, but slower |

### Template Customization

You can customize the prompt template for different model families:

**For Llama-2 based models:**
```
TEMPLATE """<s>[INST] <<SYS>>
{{.System}}
<</SYS>>

{{.Prompt}} [/INST] {{.Response}}</s>"""
```

**For Mistral/Mixtral models:**
```
TEMPLATE """<s>{{if .System}}[INST] {{.System}} [/INST]</s>
{{end}}
<s>[INST] {{.Prompt}} [/INST]
{{.Response}}</s>"""
```

## Testing and Validation

After creating a custom model, test it with challenging prompts that verify:

1. **Response completeness**: "Tell me about the history of computers in three sentences."
2. **Instruction following**: "List 5 benefits of exercise, then explain each in detail."
3. **Knowledge retrieval**: "Explain how nuclear fusion works."
4. **Reasoning capabilities**: "If a train travels at 60 mph for 2.5 hours, how far will it go? Show your steps."

## Troubleshooting

### Common Issues

1. **Model gives truncated responses**
   - Increase repeat_penalty (1.1-1.3)
   - Strengthen system prompt with explicit instructions
   - Increase num_predict parameter

2. **Responses are too generic**
   - Increase temperature (0.7-0.9)
   - Adjust top_p higher (0.9-0.95)
   - Use more specific instructions in system prompt

3. **Model is too random/incoherent**
   - Decrease temperature (0.5-0.7)
   - Lower top_k (20-40)
   - Adjust repeat_penalty higher

4. **Model runs out of context**
   - Increase num_ctx parameter
   - Simplify prompts to use less context
   - Break complex tasks into smaller parts

## Example Models

### mistral-factual (Minimizing Hallucinations)

```
FROM mistral

# Set conservative parameters to reduce hallucination
PARAMETER temperature 0.5
PARAMETER top_p 0.85
PARAMETER top_k 30
PARAMETER num_ctx 8192
PARAMETER num_predict 4096
PARAMETER repeat_penalty 1.15
PARAMETER repeat_last_n 64
PARAMETER presence_penalty 0.1

TEMPLATE """
<s>{{if .System}}[INST] {{.System}} [/INST]</s>
{{end}}
<s>[INST] {{.Prompt}} [/INST]
{{.Response}}</s>
"""

SYSTEM """You are a highly precise and factual AI assistant. Your responses must be:
1. Strictly based on verifiable information
2. Clear about uncertainty - say "I'm not certain" or "I don't have enough information" when appropriate
3. Free from speculation and assumptions
4. Focused on providing concrete, specific information rather than vague generalizations
5. Structured and logical in presentation

When responding:
- If you're not completely sure about something, explicitly state your level of confidence
- Distinguish between facts and interpretations
- Avoid making predictions or assumptions about things you can't verify
- Use precise language and avoid ambiguous terms
- If asked about current events or time-sensitive information, clarify that your knowledge has limitations

Remember: It's better to provide a shorter, accurate answer than a longer one that might contain inaccuracies."""
```

Testing the model for hallucinations:
```bash
# Test future predictions
curl -X POST "http://localhost:8002/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-factual",
    "prompt": "What will be the dominant programming language in 2030?",
    "temperature": 0.5
  }'

# Test scientific uncertainty
curl -X POST "http://localhost:8002/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral-factual",
    "prompt": "What is dark matter made of at the quantum level?",
    "temperature": 0.5
  }'
```

### mistral-fixed (Comprehensive Responses)

```