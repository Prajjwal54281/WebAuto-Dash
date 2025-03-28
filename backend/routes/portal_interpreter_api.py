                # Analyze input field names and placeholders
                form_text = ' '.join([
                    str(inp.get('name', '')),
                    str(inp.get('id', '')),
                    str(inp.get('placeholder', ''))
                    for inp in inputs
                ]).lower() 