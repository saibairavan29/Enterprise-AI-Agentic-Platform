import os
import shutil
import tempfile
import pandas as pd
from django.test import TestCase
from edqi.ml_engine.feature_pipeline import FeaturePipeline

class FeaturePipelineTestCase(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.df = pd.DataFrame([
            {"feat1": 10.0, "feat2": 5.0},
            {"feat1": None, "feat2": 15.0}, # Needs imputation
            {"feat1": 20.0, "feat2": 25.0}
        ])

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_pipeline_imputing_scaling(self):
        pipeline = FeaturePipeline()
        scaled = pipeline.fit_transform(self.df)
        
        # Non-null values mean should replace None with median (15.0)
        self.assertEqual(scaled.shape, (3, 2))
        
        # Verify transformation values are scaled (mean = ~0)
        col1_mean = scaled[:, 0].mean()
        self.assertAlmostEqual(col1_mean, 0.0, places=5)

    def test_save_load_pipeline(self):
        pipeline = FeaturePipeline()
        pipeline.fit_transform(self.df)
        
        file_path = os.path.join(self.tmp_dir, "test_pipeline.joblib")
        pipeline.save_pipeline(file_path)
        self.assertTrue(os.path.exists(file_path))
        
        loaded = FeaturePipeline.load_pipeline(file_path)
        transformed = loaded.transform(self.df)
        self.assertEqual(transformed.shape, (3, 2))
