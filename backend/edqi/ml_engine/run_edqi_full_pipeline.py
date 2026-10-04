import os
import sys
import json
import time
import hashlib
import getpass
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import joblib

# 1. SETUP PATHS & DJANGO ENVIRONMENT
BASE_DIR = r"E:\project final year\Enterprise-AI-Agentic-Platform"
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_platform.settings')
import django
django.setup()

DATASET_PATH = r"E:\project final year\Dataset Final\Datasets\Data_Quality\AB_NYC_2019.csv\AB_NYC_2019.csv"
TRAINED_MODELS_DIR = os.path.join(BASE_DIR, "trained_models")

# User Downloads Path Detection
user_name = getpass.getuser()
user_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(user_downloads, exist_ok=True)

# Also check alternate user folder if exists
alt_downloads = r"C:\Users\bharathwaj\Downloads"
if os.path.exists(r"C:\Users\bharathwaj"):
    os.makedirs(alt_downloads, exist_ok=True)

print(f"INFO Target User: {user_name}")
print(f"INFO Primary Downloads Directory: {user_downloads}")

# 2. LOAD AB_NYC_2019 BASE DATASET
print(f"INFO Loading base dataset from {DATASET_PATH}...")
df_raw = pd.read_csv(DATASET_PATH)
print(f"INFO Base Dataset Loaded: {len(df_raw)} rows, {len(df_raw.columns)} columns.")

# Filter pristine base listings
clean_mask = (
    (df_raw['price'] > 0) &
    (df_raw['name'].notnull()) &
    (df_raw['host_name'].notnull()) &
    (df_raw['minimum_nights'] > 0) & (df_raw['minimum_nights'] <= 365)
)
df_clean_base = df_raw[clean_mask].copy().reset_index(drop=True)
df_clean_base['base_record_id'] = df_clean_base['id']
print(f"INFO Pristine Base Listings Pool: {len(df_clean_base)} records.")

# 3. AMENDMENT 1: SPLIT BASE RECORDS BEFORE CORRUPTION
unique_base_ids = df_clean_base['base_record_id'].unique()
np.random.seed(42)
np.random.shuffle(unique_base_ids)

n_total_base = len(unique_base_ids)
n_train_base = int(0.70 * n_total_base)
n_val_base = int(0.15 * n_total_base)

train_base_ids = set(unique_base_ids[:n_train_base])
val_base_ids = set(unique_base_ids[n_train_base:n_train_base + n_val_base])
test_base_ids = set(unique_base_ids[n_train_base + n_val_base:])

print(f"INFO Base Records Split (Before Corruption): Train={len(train_base_ids)}, Val={len(val_base_ids)}, Test={len(test_base_ids)}")

# 4. AMENDMENT 2 & 3: VARIED SYNTHETIC CORRUPTION GENERATOR
def generate_synthetic_variants_for_base_split(base_df, split_name, random_seed=42):
    rng = np.random.RandomState(random_seed)
    synthetic_records = []
    
    for idx, row in base_df.iterrows():
        base_id = row['base_record_id']
        
        # 1. Clean Variant (Class 0: HIGH_QUALITY)
        rec_clean = row.to_dict()
        rec_clean['synthetic_record_id'] = f"SYN_{base_id}_0"
        rec_clean['corruption_type'] = "NONE"
        rec_clean['corruption_severity'] = "NONE"
        rec_clean['corruption_count'] = 0
        rec_clean['is_corrupted'] = 0
        rec_clean['quality_risk_level'] = 0  # HIGH_QUALITY
        synthetic_records.append(rec_clean)
        
        # 2. Minor Defect Variant (Class 1: MEDIUM_QUALITY)
        rec_minor = row.to_dict()
        rec_minor['synthetic_record_id'] = f"SYN_{base_id}_1"
        c_type = rng.choice(["C01_NAME_NULL", "C02_HOSTNAME_NULL", "C10_DUPLICATE_MUTATION"])
        if c_type == "C01_NAME_NULL":
            rec_minor['name'] = None
        elif c_type == "C02_HOSTNAME_NULL":
            rec_minor['host_name'] = None
        else:
            rec_minor['name'] = str(row['name']) + " (Copy)"
            
        rec_minor['corruption_type'] = c_type
        rec_minor['corruption_severity'] = "MINOR"
        rec_minor['corruption_count'] = 1
        rec_minor['is_corrupted'] = 1
        rec_minor['quality_risk_level'] = 1  # MEDIUM_QUALITY
        synthetic_records.append(rec_minor)
        
        # 3. Severe Defect Variant (Class 2: POOR_QUALITY)
        rec_severe = row.to_dict()
        rec_severe['synthetic_record_id'] = f"SYN_{base_id}_2"
        s_type = rng.choice([
            "C03_PRICE_ZERO", "C04_PRICE_EXTREME", "C05_STAY_EXTREME",
            "C06_STAY_NEGATIVE", "C07_REVIEW_NULL_MISMATCH", "C08_REVIEW_ZERO_MISMATCH",
            "C09_LATLON_OUTOFBOUNDS"
        ])
        if s_type == "C03_PRICE_ZERO":
            rec_severe['price'] = rng.choice([0, -10, -50, -100])
        elif s_type == "C04_PRICE_EXTREME":
            rec_severe['price'] = rng.randint(25000, 100000)
        elif s_type == "C05_STAY_EXTREME":
            rec_severe['minimum_nights'] = rng.randint(366, 1500)
        elif s_type == "C06_STAY_NEGATIVE":
            rec_severe['minimum_nights'] = rng.randint(-30, -1)
        elif s_type == "C07_REVIEW_NULL_MISMATCH":
            rec_severe['number_of_reviews'] = rng.randint(10, 200)
            rec_severe['last_review'] = None
            rec_severe['reviews_per_month'] = None
        elif s_type == "C08_REVIEW_ZERO_MISMATCH":
            rec_severe['number_of_reviews'] = 0
            rec_severe['last_review'] = "2019-07-01"
            rec_severe['reviews_per_month'] = 2.5
        elif s_type == "C09_LATLON_OUTOFBOUNDS":
            rec_severe['latitude'] = rng.uniform(42.0, 80.0)
            
        rec_severe['corruption_type'] = s_type
        rec_severe['corruption_severity'] = "SEVERE"
        rec_severe['corruption_count'] = 1
        rec_severe['is_corrupted'] = 1
        rec_severe['quality_risk_level'] = 2  # POOR_QUALITY
        synthetic_records.append(rec_severe)

    df_synth = pd.DataFrame(synthetic_records)
    print(f"INFO Generated {len(df_synth)} synthetic records for {split_name} split.")
    return df_synth

df_train_base = df_clean_base[df_clean_base['base_record_id'].isin(train_base_ids)].reset_index(drop=True)
df_val_base = df_clean_base[df_clean_base['base_record_id'].isin(val_base_ids)].reset_index(drop=True)
df_test_base = df_clean_base[df_clean_base['base_record_id'].isin(test_base_ids)].reset_index(drop=True)

df_train_synth = generate_synthetic_variants_for_base_split(df_train_base, "Train", random_seed=42)
df_val_synth = generate_synthetic_variants_for_base_split(df_val_base, "Validation", random_seed=43)
df_test_synth = generate_synthetic_variants_for_base_split(df_test_base, "Test", random_seed=44)

# Calculate SHA256 dataset hash
full_df = pd.concat([df_train_synth, df_val_synth, df_test_synth], ignore_index=True)
csv_bytes = full_df.to_csv(index=False).encode('utf-8')
dataset_hash = hashlib.sha256(csv_bytes).hexdigest()
dataset_version = "v3.0.0_ABNYC"

print(f"INFO Synthetic Dataset Generated. Total Records: {len(full_df)} (Train={len(df_train_synth)}, Val={len(df_val_synth)}, Test={len(df_test_synth)})")
print(f"INFO Dataset Version: {dataset_version}, SHA256: {dataset_hash[:16]}...")

# 5. AMENDMENT 7: FEATURE TRANSFORMATIONS FIT ON TRAIN ONLY
def compute_train_group_stats(df_tr):
    df_tr_copy = df_tr.copy()
    df_tr_copy['price_clean'] = df_tr_copy['price'].apply(lambda x: float(x) if x is not None and not pd.isna(x) else 0.0)
    df_tr_copy['price_log'] = np.log1p(np.maximum(0.0, df_tr_copy['price_clean']))
    stats = {}
    for rtype, group in df_tr_copy.groupby('room_type'):
        mean_v = float(group['price_log'].mean())
        std_v = float(group['price_log'].std())
        if std_v <= 1e-6 or pd.isna(std_v): std_p = 1.0
        else: std_p = std_v
        stats[str(rtype).strip()] = {"mean": mean_v, "std": std_p}
    return stats

train_group_stats = compute_train_group_stats(df_train_synth)
print(f"INFO Computed Room Type Group Statistics strictly on Training Split: {train_group_stats}")

def extract_feature_matrix(df_split, group_stats):
    from edqi.feature_engineering.feature_generator import FeatureGenerator, NON_LEAKY_FEATURE_NAMES
    X_rows = []
    y_labels = []
    for idx, row in df_split.iterrows():
        row_dict = row.to_dict()
        feats = FeatureGenerator.extract_record_features(row_dict, group_stats=group_stats)
        clean_feats = [feats[col] for col in NON_LEAKY_FEATURE_NAMES]
        X_rows.append(clean_feats)
        y_labels.append(row_dict['quality_risk_level'])
        
    X = pd.DataFrame(X_rows, columns=NON_LEAKY_FEATURE_NAMES)
    y = pd.Series(y_labels)
    return X, y

X_train_raw, y_train = extract_feature_matrix(df_train_synth, train_group_stats)
X_val_raw, y_val = extract_feature_matrix(df_val_synth, train_group_stats)
X_test_raw, y_test = extract_feature_matrix(df_test_synth, train_group_stats)

# Fit StandardScaler ONLY on Training set
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train_raw)
X_val = scaler.transform(X_val_raw)
X_test = scaler.transform(X_test_raw)

print(f"INFO Feature Matrices Prepared. X_train shape: {X_train.shape}, X_val shape: {X_val.shape}, X_test shape: {X_test.shape}")

# 6. MODEL TRAINING & EVALUATION
CLASS_NAMES = ["HIGH_QUALITY", "MEDIUM_QUALITY", "POOR_QUALITY"]
feature_names = list(X_train_raw.columns)

# 6A. Random Forest
print("INFO Training Random Forest Classifier...")
t0_rf = time.time()
rf_model = RandomForestClassifier(n_estimators=300, max_depth=12, random_state=42, n_jobs=-1)
rf_model.fit(X_train, y_train)
t_train_rf = time.time() - t0_rf

t0_pred = time.time()
y_pred_rf = rf_model.predict(X_test)
y_prob_rf = rf_model.predict_proba(X_test)
t_pred_rf = time.time() - t0_pred

acc_rf = accuracy_score(y_test, y_pred_rf)
prec_rf = precision_score(y_test, y_pred_rf, average='macro')
rec_rf = recall_score(y_test, y_pred_rf, average='macro')
f1_macro_rf = f1_score(y_test, y_pred_rf, average='macro')
f1_weighted_rf = f1_score(y_test, y_pred_rf, average='weighted')
roc_auc_rf = roc_auc_score(y_test, y_prob_rf, multi_class='ovr')
cm_rf = confusion_matrix(y_test, y_pred_rf)

# 5-Fold Stratified CV on Train+Val
X_cv = np.vstack([X_train, X_val])
y_cv = np.concatenate([y_train, y_val])
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores_rf = []
for tr_idx, val_idx in skf.split(X_cv, y_cv):
    m = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    m.fit(X_cv[tr_idx], y_cv[tr_idx])
    cv_scores_rf.append(m.score(X_cv[val_idx], y_cv[val_idx]))
cv_score_rf = float(np.mean(cv_scores_rf))

print(f"INFO RF Results: Accuracy={acc_rf:.4f}, Macro F1={f1_macro_rf:.4f}, 5-Fold CV={cv_score_rf:.4f}")

# 6B. XGBoost
print("INFO Training XGBoost Classifier...")
t0_xgb = time.time()
xgb_model = XGBClassifier(
    n_estimators=300, learning_rate=0.05, max_depth=6,
    subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1,
    eval_metric='mlogloss'
)
xgb_model.fit(X_train, y_train)
t_train_xgb = time.time() - t0_xgb

t0_pred = time.time()
y_pred_xgb = xgb_model.predict(X_test)
y_prob_xgb = xgb_model.predict_proba(X_test)
t_pred_xgb = time.time() - t0_pred

acc_xgb = accuracy_score(y_test, y_pred_xgb)
prec_xgb = precision_score(y_test, y_pred_xgb, average='macro')
rec_xgb = recall_score(y_test, y_pred_xgb, average='macro')
f1_macro_xgb = f1_score(y_test, y_pred_xgb, average='macro')
f1_weighted_xgb = f1_score(y_test, y_pred_xgb, average='weighted')
roc_auc_xgb = roc_auc_score(y_test, y_prob_xgb, multi_class='ovr')
cm_xgb = confusion_matrix(y_test, y_pred_xgb)

cv_scores_xgb = []
for tr_idx, val_idx in skf.split(X_cv, y_cv):
    m = XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=5, random_state=42, n_jobs=-1, eval_metric='mlogloss')
    m.fit(X_cv[tr_idx], y_cv[tr_idx])
    cv_scores_xgb.append(m.score(X_cv[val_idx], y_cv[val_idx]))
cv_score_xgb = float(np.mean(cv_scores_xgb))

print(f"INFO XGB Results: Accuracy={acc_xgb:.4f}, Macro F1={f1_macro_xgb:.4f}, 5-Fold CV={cv_score_xgb:.4f}")

# 7. SAVE MACHINE-READABLE RESULTS JSON
model_version_rf = "RF_v2.0.0_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S")
model_version_xgb = "XGB_v2.0.0_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S")

results_dict = {
    "title": "FINAL EDQI MODEL EVALUATION",
    "evaluation_timestamp": datetime.utcnow().isoformat() + "Z",
    "dataset_metadata": {
        "dataset_name": "AB_NYC_2019 Controlled Synthetic Quality Dataset",
        "dataset_version": dataset_version,
        "dataset_hash": dataset_hash,
        "random_seed": 42,
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "class_names": CLASS_NAMES,
        "total_dataset_size": len(full_df),
        "training_set_size": len(X_train),
        "validation_set_size": len(X_val),
        "test_set_size": len(X_test)
    },
    "random_forest": {
        "algorithm": "Random Forest Classifier",
        "model_version": model_version_rf,
        "accuracy": float(acc_rf),
        "precision": float(prec_rf),
        "recall": float(rec_rf),
        "f1_score": float(f1_macro_rf),
        "macro_f1": float(f1_macro_rf),
        "weighted_f1": float(f1_weighted_rf),
        "roc_auc": float(roc_auc_rf),
        "cross_validation_score": float(cv_score_rf),
        "training_time_sec": float(t_train_rf),
        "prediction_time_sec": float(t_pred_rf),
        "confusion_matrix": cm_rf.tolist(),
        "feature_importances": dict(zip(feature_names, rf_model.feature_importances_.tolist()))
    },
    "xgboost": {
        "algorithm": "XGBoost Classifier",
        "model_version": model_version_xgb,
        "accuracy": float(acc_xgb),
        "precision": float(prec_xgb),
        "recall": float(rec_xgb),
        "f1_score": float(f1_macro_xgb),
        "macro_f1": float(f1_macro_xgb),
        "weighted_f1": float(f1_weighted_xgb),
        "roc_auc": float(roc_auc_xgb),
        "cross_validation_score": float(cv_score_xgb),
        "training_time_sec": float(t_train_xgb),
        "prediction_time_sec": float(t_pred_xgb),
        "confusion_matrix": cm_xgb.tolist(),
        "feature_importances": dict(zip(feature_names, xgb_model.feature_importances_.tolist()))
    }
}

json_path = os.path.join(TRAINED_MODELS_DIR, "EDQI_FINAL_MODEL_EVALUATION.json")
with open(json_path, "w") as f:
    json.dump(results_dict, f, indent=4)
print(f"INFO Evaluation JSON saved to: {json_path}")

# Also save JSON copy to user Downloads directory
dl_json_path = os.path.join(user_downloads, "EDQI_FINAL_MODEL_EVALUATION.json")
with open(dl_json_path, "w") as f:
    json.dump(results_dict, f, indent=4)
print(f"INFO Evaluation JSON copy saved to Downloads: {dl_json_path}")

# 8. PERSIST MODEL ARTIFACTS IN PERSISTENT REGISTRY
os.makedirs(os.path.join(TRAINED_MODELS_DIR, "random_forest", model_version_rf), exist_ok=True)
os.makedirs(os.path.join(TRAINED_MODELS_DIR, "xgboost", model_version_xgb), exist_ok=True)
os.makedirs(os.path.join(TRAINED_MODELS_DIR, "pipelines"), exist_ok=True)

joblib.dump(rf_model, os.path.join(TRAINED_MODELS_DIR, "random_forest", model_version_rf, "classifier.joblib"))
joblib.dump(xgb_model, os.path.join(TRAINED_MODELS_DIR, "xgboost", model_version_xgb, "classifier.joblib"))
joblib.dump(scaler, os.path.join(TRAINED_MODELS_DIR, "pipelines", "feature_pipeline.joblib"))

print("INFO Model Artifacts successfully persisted in persistent registry.")

# 9. RENDER HIGH-RESOLUTION EVALUATION RESULTS IMAGE
plt.figure(figsize=(18, 14), dpi=300)
plt.style.use('dark_background')

# Title & Banner
plt.suptitle("FINAL EDQI MODEL EVALUATION", fontsize=24, fontweight='bold', color='#38bdf8', y=0.98)
plt.figtext(0.5, 0.94, f"Dataset: AB_NYC_2019 ({len(full_df):,} records) | Features: 10 Non-Leaky Vectors | Seed: 42 | Split: 70/15/15", 
            ha='center', fontsize=12, color='#94a3b8')

# Table Subplot 1: Random Forest Metrics
ax1 = plt.subplot(2, 2, 1)
ax1.axis('off')
ax1.set_title("Random Forest Evaluation Summary", fontsize=14, fontweight='bold', color='#34d399', pad=10)

rf_table_data = [
    ["Metric", "Measured Value"],
    ["Model Version", model_version_rf],
    ["Accuracy", f"{acc_rf*100:.2f}%"],
    ["Precision (Macro)", f"{prec_rf*100:.2f}%"],
    ["Recall (Macro)", f"{rec_rf*100:.2f}%"],
    ["Macro F1-Score", f"{f1_macro_rf:.4f}"],
    ["Weighted F1-Score", f"{f1_weighted_rf:.4f}"],
    ["ROC-AUC (OVR)", f"{roc_auc_rf:.4f}"],
    ["5-Fold CV Score", f"{cv_score_rf*100:.2f}%"],
    ["Training Time", f"{t_train_rf:.3f} sec"],
    ["Inference Time", f"{t_pred_rf*1000:.2f} ms"]
]

t1 = ax1.table(cellText=rf_table_data, loc='center', cellLoc='left', colWidths=[0.45, 0.55])
t1.auto_set_font_size(False)
t1.set_fontsize(11)
t1.scale(1.1, 1.4)
for (r, c), cell in t1.get_celld().items():
    if r == 0:
        cell.set_facecolor('#1e293b')
        cell.set_text_props(weight='bold', color='#f8fafc')
    else:
        cell.set_facecolor('#0f172a')
        cell.set_text_props(color='#e2e8f0')

# Confusion Matrix Subplot 2: Random Forest
ax2 = plt.subplot(2, 2, 2)
sns.heatmap(cm_rf, annot=True, fmt='d', cmap='Blues', cbar=False, ax=ax2,
            xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
ax2.set_title("Random Forest Confusion Matrix", fontsize=14, fontweight='bold', color='#34d399', pad=10)
ax2.set_xlabel("Predicted Label", color='#94a3b8')
ax2.set_ylabel("True Label", color='#94a3b8')

# Table Subplot 3: XGBoost Metrics
ax3 = plt.subplot(2, 2, 3)
ax3.axis('off')
ax3.set_title("XGBoost Evaluation Summary", fontsize=14, fontweight='bold', color='#f43f5e', pad=10)

xgb_table_data = [
    ["Metric", "Measured Value"],
    ["Model Version", model_version_xgb],
    ["Accuracy", f"{acc_xgb*100:.2f}%"],
    ["Precision (Macro)", f"{prec_xgb*100:.2f}%"],
    ["Recall (Macro)", f"{rec_xgb*100:.2f}%"],
    ["Macro F1-Score", f"{f1_macro_xgb:.4f}"],
    ["Weighted F1-Score", f"{f1_weighted_xgb:.4f}"],
    ["ROC-AUC (OVR)", f"{roc_auc_xgb:.4f}"],
    ["5-Fold CV Score", f"{cv_score_xgb*100:.2f}%"],
    ["Training Time", f"{t_train_xgb:.3f} sec"],
    ["Inference Time", f"{t_pred_xgb*1000:.2f} ms"]
]

t3 = ax3.table(cellText=xgb_table_data, loc='center', cellLoc='left', colWidths=[0.45, 0.55])
t3.auto_set_font_size(False)
t3.set_fontsize(11)
t3.scale(1.1, 1.4)
for (r, c), cell in t3.get_celld().items():
    if r == 0:
        cell.set_facecolor('#1e293b')
        cell.set_text_props(weight='bold', color='#f8fafc')
    else:
        cell.set_facecolor('#0f172a')
        cell.set_text_props(color='#e2e8f0')

# Confusion Matrix Subplot 4: XGBoost
ax4 = plt.subplot(2, 2, 4)
sns.heatmap(cm_xgb, annot=True, fmt='d', cmap='Reds', cbar=False, ax=ax4,
            xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
ax4.set_title("XGBoost Confusion Matrix", fontsize=14, fontweight='bold', color='#f43f5e', pad=10)
ax4.set_xlabel("Predicted Label", color='#94a3b8')
ax4.set_ylabel("True Label", color='#94a3b8')

# Metadata Footer Box
footer_text = f"Dataset Hash: {dataset_hash[:32]}... | Training Set: {len(X_train):,} | Validation Set: {len(X_val):,} | Test Set: {len(X_test):,}"
plt.figtext(0.5, 0.02, footer_text, ha='center', fontsize=11, color='#64748b', bbox=dict(boxstyle='round', facecolor='#0f172a', alpha=0.8))

plt.tight_layout(rect=[0, 0.04, 1, 0.93])

# Save PNG image to primary User Downloads folder
img_primary_path = os.path.join(user_downloads, "EDQI_FINAL_MODEL_EVALUATION.png")
timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
img_timestamp_path = os.path.join(user_downloads, f"EDQI_FINAL_MODEL_EVALUATION_{timestamp_str}.png")

plt.savefig(img_primary_path, dpi=300, bbox_inches='tight')
plt.savefig(img_timestamp_path, dpi=300, bbox_inches='tight')

# Save copy to alternate Downloads path if exists
if os.path.exists(r"C:\Users\bharathwaj"):
    alt_primary = os.path.join(alt_downloads, "EDQI_FINAL_MODEL_EVALUATION.png")
    plt.savefig(alt_primary, dpi=300, bbox_inches='tight')
    print(f"INFO Saved alternate image copy to: {alt_primary}")

plt.close()

print(f"INFO High-Resolution Evaluation Image saved to: {img_primary_path}")
print(f"INFO Timestamped Evaluation Image saved to: {img_timestamp_path}")

# Verify file existence and non-zero size
if os.path.exists(img_primary_path) and os.path.getsize(img_primary_path) > 0:
    print(f"VERIFIED: {img_primary_path} exists ({os.path.getsize(img_primary_path):,} bytes).")
else:
    print(f"ERROR: Image verification failed for {img_primary_path}")

if os.path.exists(dl_json_path) and os.path.getsize(dl_json_path) > 0:
    print(f"VERIFIED: {dl_json_path} exists ({os.path.getsize(dl_json_path):,} bytes).")
else:
    print(f"ERROR: JSON verification failed for {dl_json_path}")
