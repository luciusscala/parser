# FastAPI Web Parser with LLM Extraction

A high-performance FastAPI application that parses JavaScript-heavy websites and extracts structured data using OpenAI's LLM.

## Features

- **Fast Rendering**: Uses Playwright for efficient browser automation
- **Content Pre-parsing**: Removes boilerplate (scripts, styles, navigation) before LLM processing
- **LLM Extraction**: Uses OpenAI to extract structured JSON data based on customizable prompts
- **Optimized Performance**: Targets <10 second response times
- **Async Architecture**: Fully asynchronous for maximum throughput

## Installation

1. Clone the repository and navigate to the project directory:
```bash
cd parser
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

5. Create a `.env` file from the example:
```bash
cp .env.example .env
```

6. Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Starting the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### API Endpoint

#### POST `/parse`

Parse a website and extract structured data.

**Request:**
```json
{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "field1": "value1",
  "field2": "value2",
  ...
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Configuration

Environment variables (in `.env` file):

- `OPENAI_API_KEY` (required): Your OpenAI API key
- `OPENAI_MODEL` (optional): Model to use (default: `gpt-4-turbo-preview`)
- `BROWSER_TIMEOUT` (optional): Browser timeout in milliseconds (default: 6000)
- `LLM_TIMEOUT` (optional): LLM timeout in milliseconds (default: 30000)
- `PROMPT_FILE` (optional): Path to prompt file (default: `prompts/prompt.txt`)

## Customizing Extraction

Edit `prompts/prompt.txt` to customize what data is extracted and in what format. The prompt should instruct the LLM on:
- What data to extract
- The JSON structure to return
- Any specific formatting requirements

## Performance Optimizations

- **Browser Reuse**: Single browser instance shared across requests
- **Resource Blocking**: Images, fonts, and stylesheets are blocked to speed up loading
- **Content Pre-parsing**: Boilerplate removal reduces tokens sent to LLM by 40-70%
- **Selective Waiting**: Only waits for DOM content, not full page load
- **Async Operations**: All I/O operations are asynchronous

## Architecture

- `app/main.py`: FastAPI application and endpoint definitions
- `app/browser.py`: Playwright browser management
- `app/preparser.py`: Content cleaning and boilerplate removal
- `app/extractor.py`: OpenAI LLM integration
- `app/config.py`: Configuration management
- `prompts/prompt.txt`: LLM extraction prompt template

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Invalid request (e.g., invalid URL)
- `500`: Internal server error
- `504`: Timeout error

## License

MIT

