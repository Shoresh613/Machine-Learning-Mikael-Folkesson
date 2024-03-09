# Part 1.4 of the project, final part of the first part of the project

import pandas as pd
from joblib import load

# Load the data
test_samples = pd.read_csv('./save/test_samples.csv')
bmi_rf_clf = load('./save/best_rf_cat.pkl') 

probabilities = bmi_rf_clf.predict_proba(test_samples.drop(['cardio','Unnamed: 0'], axis=1))
predictions = bmi_rf_clf.predict(test_samples.drop(['cardio','Unnamed: 0'], axis=1))

predictions_df = pd.DataFrame({
    'probability class 0': probabilities[:, 0], # Slicing all rows and the first column
    'probability class 1': probabilities[:, 1],
    'prediction': predictions
})

print(predictions_df.head())
predictions_df.to_csv('./save/eval_df.csv', index=False)

# Compare the predictions with the actual values
predictions_df['actual'] = test_samples['cardio']
predictions_df['correct'] = predictions_df['prediction'] == predictions_df['actual']
print(f"\n{predictions_df.head()}")
print("Accuracy: ", predictions_df['correct'].sum() / predictions_df['correct'].count())
