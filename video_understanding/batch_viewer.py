import json
from pathlib import Path
from typing import Dict, List


class BatchViewer:
    """Creates an HTML viewer to see all batches side by side"""
    
    def __init__(self, cache_dir: str = "batch_cache"):
        self.cache_dir = Path(cache_dir)
    
    def generate_viewer(self, output_file: str = "batch_viewer.html") -> None:
        """Generate an HTML file showing all batches side by side"""
        batch_data = self._load_all_batches()
        
        html = self._create_html(batch_data)
        
        with open(output_file, 'w') as f:
            f.write(html)
        
        print(f"Batch viewer created: {output_file}")
        print("Open this file in your browser to see all batches side by side")
    
    def _load_all_batches(self) -> List[Dict]:
        """Load all cached batch data"""
        batch_files = sorted(self.cache_dir.glob("batch_*_state.json"))
        batches = []
        
        for batch_file in batch_files:
            try:
                with open(batch_file, 'r') as f:
                    data = json.load(f)
                    batches.append(data)
            except Exception as e:
                print(f"Error loading {batch_file}: {e}")
        
        return batches
    
    def _create_html(self, batch_data: List[Dict]) -> str:
        """Create the HTML content"""
        
        # Create navigation tabs
        nav_tabs = ""
        tab_content = ""
        
        for i, batch in enumerate(batch_data):
            batch_num = batch.get('batch_num', i)
            active_class = "active" if i == 0 else ""
            
            nav_tabs += f'<button class="tab-button {active_class}" onclick="showBatch({batch_num})" id="tab-{batch_num}">Batch {batch_num + 1}</button>'
            
            # Get the full data
            response = batch.get('response', {})
            
            # Try to find corresponding GIF and prompt
            gif_path = f"batch_{batch_num:03d}_movie.gif"
            gif_exists = (self.cache_dir / gif_path).exists()
            
            # Read the debug file for the prompt (if it exists)
            debug_file = f"debug_batch_{batch_num:03d}.txt"
            prompt_content = "No prompt available"
            if Path(debug_file).exists():
                try:
                    with open(debug_file, 'r') as f:
                        debug_content = f.read()
                        if "--- FULL PROMPT ---" in debug_content:
                            prompt_content = debug_content.split("--- FULL PROMPT ---\n", 1)[1]
                except Exception:
                    pass
            
            # Format JSON nicely
            response_json = json.dumps(response, indent=2, default=str)
            persistent_json = json.dumps({
                'persistent_goal_state': batch.get('persistent_goal_state'),
                'persistent_current_state': batch.get('persistent_current_state'),
                'persistent_protocol_log': batch.get('persistent_protocol_log'),
                'persistent_warnings': batch.get('persistent_warnings')
            }, indent=2, default=str)
            
            tab_content += f"""
            <div class="batch-content {active_class}" id="batch-{batch_num}">
                <div class="batch-layout">
                    <div class="video-section">
                        <h4>📹 Video Frames</h4>
                        {f'<img src="{self.cache_dir}/{gif_path}" alt="Batch {batch_num + 1} GIF" class="batch-gif">' if gif_exists else '<div class="no-gif">No GIF available</div>'}
                    </div>
                    
                    <div class="prompt-section">
                        <h4>📝 Prompt</h4>
                        <pre class="code-block">{prompt_content}</pre>
                    </div>
                    
                    <div class="response-section">
                        <h4>🤖 Response JSON</h4>
                        <pre class="code-block">{response_json}</pre>
                    </div>
                    
                    <div class="persistent-section">
                        <h4>💾 Persistent State</h4>
                        <pre class="code-block">{persistent_json}</pre>
                    </div>
                </div>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Batch Viewer - Detailed View</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 0;
                    background-color: #f5f5f5;
                }}
                .header {{
                    text-align: center;
                    padding: 20px;
                    background: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin-bottom: 0;
                }}
                .nav-tabs {{
                    display: flex;
                    background: white;
                    border-bottom: 1px solid #ddd;
                    overflow-x: auto;
                }}
                .tab-button {{
                    padding: 12px 20px;
                    border: none;
                    background: none;
                    cursor: pointer;
                    border-bottom: 3px solid transparent;
                    font-size: 14px;
                    white-space: nowrap;
                }}
                .tab-button.active {{
                    border-bottom-color: #007bff;
                    background: #f8f9fa;
                }}
                .tab-button:hover {{
                    background: #f8f9fa;
                }}
                .batch-content {{
                    display: none;
                    padding: 20px;
                }}
                .batch-content.active {{
                    display: block;
                }}
                .batch-layout {{
                    display: grid;
                    grid-template-columns: 300px 1fr 1fr;
                    grid-template-rows: auto auto;
                    gap: 20px;
                    height: calc(100vh - 160px);
                }}
                .video-section {{
                    grid-row: span 2;
                }}
                .prompt-section, .response-section, .persistent-section {{
                    background: white;
                    border-radius: 8px;
                    padding: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .batch-gif {{
                    width: 100%;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    background: white;
                    padding: 10px;
                }}
                .no-gif {{
                    width: 100%;
                    height: 200px;
                    background: #eee;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    color: #666;
                }}
                .code-block {{
                    background: #f8f9fa;
                    border: 1px solid #e9ecef;
                    border-radius: 4px;
                    padding: 12px;
                    margin: 0;
                    overflow: auto;
                    max-height: calc(50vh - 80px);
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    line-height: 1.4;
                    white-space: pre-wrap;
                }}
                h4 {{
                    margin: 0 0 10px 0;
                    color: #333;
                    font-size: 16px;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎬 Batch Viewer - Detailed View</h1>
                <p>Video + Prompt + JSON for each batch</p>
            </div>
            
            <div class="nav-tabs">
                {nav_tabs}
            </div>
            
            {tab_content}
            
            <script>
                function showBatch(batchNum) {{
                    // Hide all batch contents
                    const contents = document.querySelectorAll('.batch-content');
                    contents.forEach(content => content.classList.remove('active'));
                    
                    // Remove active class from all tabs
                    const tabs = document.querySelectorAll('.tab-button');
                    tabs.forEach(tab => tab.classList.remove('active'));
                    
                    // Show selected batch
                    document.getElementById(`batch-${{batchNum}}`).classList.add('active');
                    document.getElementById(`tab-${{batchNum}}`).classList.add('active');
                }}
            </script>
        </body>
        </html>
        """


def create_batch_viewer(cache_dir: str = "batch_cache") -> None:
    """Convenience function to create batch viewer"""
    viewer = BatchViewer(cache_dir)
    viewer.generate_viewer()