# denied-inference-modelling

from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

matching_features = [
    "age",
    "cohort",
    "state_of_residence",
    "income_range"
]

X = df[matching_features]

preprocessor = ColumnTransformer(
    [
        ("num", StandardScaler(), ["age"]),
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore"),
            ["cohort", "state_of_residence", "income_range"]
        )
    ]
)

X_enc = preprocessor.fit_transform(X)







idx1 = df["risk_group"] == 1
idx6 = df["risk_group"] == 6

X1 = X_enc[idx1]
X6 = X_enc[idx6]

df1 = df[idx1].reset_index(drop=True)
df6 = df[idx6].reset_index(drop=True)





from sklearn.neighbors import NearestNeighbors

nn = NearestNeighbors(
    n_neighbors=1,
    metric="euclidean"
)

nn.fit(X6)

distances, indices = nn.kneighbors(X1)







results = []

for i, (dist, idx) in enumerate(zip(distances[:,0], indices[:,0])):
    
    row1 = df1.iloc[i]
    row6 = df6.iloc[idx]

    results.append({
        "id_risk1": row1["ID"],
        "id_risk6": row6["ID"],
        "distance": dist,
        "age_1": row1["age"],
        "age_6": row6["age"],
        "cohort": row1["cohort"],
        "state_1": row1["state_of_residence"],
        "state_6": row6["state_of_residence"],
        "income_1": row1["income_range"],
        "income_6": row6["income_range"]
    })

pairs = pd.DataFrame(results)

pairs.sort_values("distance").head(20)
