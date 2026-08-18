def analyze_confidence(tsv_data):
    """
    Parses Tesseract TSV string, ignores -1 / NaN / empty, and calculates:
    - Average confidence
    - Minimum confidence
    - Maximum confidence
    - Median confidence
    - Word count
    - Character count
    """
    confidences = []
    word_count = 0
    char_count = 0
    
    lines = tsv_data.strip().split('\n')
    if len(lines) <= 1:
        return {
            "average": 0.0,
            "minimum": 0.0,
            "maximum": 0.0,
            "median": 0.0,
            "word_count": 0,
            "char_count": 0
        }
        
    header = lines[0].split('\t')
    try:
        conf_idx = header.index('conf')
        text_idx = header.index('text')
    except ValueError:
        return {
            "average": 0.0,
            "minimum": 0.0,
            "maximum": 0.0,
            "median": 0.0,
            "word_count": 0,
            "char_count": 0
        }
        
    for line in lines[1:]:
        cols = line.split('\t')
        if len(cols) <= max(conf_idx, text_idx):
            continue
            
        conf_str = cols[conf_idx].strip()
        word_text = cols[text_idx].strip()
        
        # Word text check
        if not word_text:
            continue
            
        try:
            conf_val = float(conf_str)
            # Skip Tesseract spacer confidences (typically -1 or out of bounds)
            if conf_val < 0.0 or conf_val > 100.0:
                continue
                
            confidences.append(conf_val)
            word_count += 1
            char_count += len(word_text)
        except ValueError:
            continue

    if not confidences:
        return {
            "average": 0.0,
            "minimum": 0.0,
            "maximum": 0.0,
            "median": 0.0,
            "word_count": word_count,
            "char_count": char_count
        }

    sorted_confs = sorted(confidences)
    n = len(sorted_confs)
    
    avg_conf = sum(sorted_confs) / n
    min_conf = sorted_confs[0]
    max_conf = sorted_confs[-1]
    
    if n % 2 == 1:
        med_conf = sorted_confs[n // 2]
    else:
        med_conf = (sorted_confs[(n // 2) - 1] + sorted_confs[n // 2]) / 2.0

    return {
        "average": round(avg_conf, 2),
        "minimum": round(min_conf, 2),
        "maximum": round(max_conf, 2),
        "median": round(med_conf, 2),
        "word_count": word_count,
        "char_count": char_count
    }
