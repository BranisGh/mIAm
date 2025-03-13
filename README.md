# **mIAm**

🚀 **mIAm** is a powerful tool for culinary assistance.

---

## **Installation Guide**

### **1️⃣ Clone the Repository**
Run the following command to clone the repository:
```bash
git clone https://github.com/BranisGh/mIAm.git
cd mIAm  # Navigate to the project directory
```

---

### **2️⃣ Set Up a Virtual Environment**
We recommend using [`uv`](https://docs.astral.sh/uv/getting-started/installation/) to manage dependencies efficiently.

#### **🔹 Install `uv`**
Follow the official [installation guide](https://docs.astral.sh/uv/getting-started/installation/).

#### **🔹 Create and Activate a Virtual Environment**
```bash
uv venv .venv  # Create the virtual environment
source .venv/bin/activate  # Activate it
```

#### **🔹 Install Dependencies**
```bash
uv pip install -e .
```

---

### **3️⃣ Set Up PostgreSQL Locally**
#### **🔹 Install `PostgreSQL`**
Follow the official [installation guide](https://www.postgresql.org/download/).

#### **🔹 Install `pgAdmin 4`**
Follow the official [installation guide](https://www.pgadmin.org/download/).

---

### **4️⃣ Add API Keys in `.env` File**
Create a `.env` file and add your API credentials:
```ini
# LLM Model - Get key at https://platform.openai.com/api-keys
OPENAI_API_KEY="XXXXX"

# LangSmith - Get key at https://smith.langchain.com
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY="XXXXX"
LANGCHAIN_PROJECT="XXXXX"

# Pinecone Vector Database - Get key at https://app.pinecone.io
PINECONE_INDEX_NAME="XXXXX"
PINECONE_API_HOST="XXXXX"
PINECONE_API_KEY="XXXXX"
PINECONE_NAMESPACE="XXXXX"

# Cohere - Get key at https://dashboard.cohere.com/api-keys
COHERE_API_KEY="XXXXX"

# Tavily - Get key at https://app.tavily.com/
TAVILY_API_KEY="XXXXX"

# PostgreSQL Database
PSQL_USERNAME="XXXXX"
PSQL_PASSWORD="XXXXX"
PSQL_HOST="127.0.0.1"
PSQL_PORT="5432"
PSQL_DATABASE="postgres"
PSQL_SSLMODE="disable"
```
---

## **Contributing**
🤝 Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a new branch: `git checkout -b feature-xyz`.
3. Make your changes and commit: `git commit -m "Add feature xyz"`.
4. Push to the branch: `git push origin feature-xyz`.
5. Open a Pull Request.

---

## **License**
📝 This project is licensed under the [MIT License](LICENSE).

---

### **🔗 Resources**
- [Official Documentation](#) *(Add relevant links)*
- [Issue Tracker](#) *(Link to GitHub Issues if applicable)*

---

### **📬 Need Help?**
If you encounter any issues, feel free to open an issue or contact [your email or Discord].

