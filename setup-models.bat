@echo off
echo Setting up custom models for Lowkey Llama...

echo Creating mistral-fixed model...
ollama create mistral-fixed -f models/mistral-fixed.modelfile

echo Done!
pause 