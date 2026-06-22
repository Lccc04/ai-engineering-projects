FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p data/raw data/chunks data/indexes

# 预下载嵌入模型（可选，首次启动时自动下载）
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-code-v1.5')" || true
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-base')" || true

EXPOSE 8000

CMD ["python", "main.py"]
