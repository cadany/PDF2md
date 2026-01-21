# pdf2md

## 项目介绍

对PDF格式的应标文件进行分析，提取文件中的文字内容，并对文件中的图片进行OCR识别，最后将提取出的文字内容保存为Markdown格式的文件。

## 功能介绍

* 对PDF文档进行转换，将PDF文档转换为文本文件。
* 对PDF文档中包含的图片进行OCR识别，提取图片中的文字。
* 对转换后的文本文件进行后处理，包括段落间距、字体大小、图片位置等。

## 环境依赖

* Python 3.12.6

#### 环境准备

##### 创建虚拟环境
```
brew install pyenv
pyenv install 3.12.6
pyenv list

# 配置shell（以zsh为例）
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

python -m venv .venv312

# 激活虚拟环境
source .venv312/bin/activate

```

##### 安装依赖
```
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

#### 运行项目

```
# PDF转换为Markdown
python backend/service/pdf_converter_v2.py ./files/fj-23p374.pdf -o ./fj-23p374.md

输出文件: ../files/fj-23p374.md
处理页面: 374
发现表格: 0
处理时间: 3993.14秒

# OCR识别图片中的文字
python backend/test/test_ocr_service.py
```
## 开发

### 接口
   - `/api/file/upload`：上传文件，返回文件id。
   - `/api/file/delete`：传入文件id，删除文件。
   - `/api/file/list`：返回服务器上所有已上传文件的信息。
   - `/api/file/convert2md`：传入文件id，将文件转换为Markdown格式。
   - `/api/file/convert2md/result`：传入任务id，返回文件转换任务结果。

## 接口详情

1、文件上传接口 
* URL：ai.pdf2md.file-upload-url
* 请求示例：
```curl --location 'http://192.168.101.21:38111/api/file/upload' \
--header 'X-API-Key: 12345' \
--form 'file=@"/Users/cadany/Desktop/标书训练/福建/福建税务/投标文件（商务部分）-福建税务2025年对外公开电话整合呼叫中心扩容项目-1029-llj审_副本2.pdf"'
```
* 响应示例：
```
{
    "status_code": 200,
    "file_id": "file-20260111143725-gfNj9jlE",
    "message": "文件上传成功",
    "file_info": {
        "original_filename": "投标文件（商务部分）-福建税务2025年对外公开电话整合呼叫中心扩容项目-1029-llj审_副本2.pdf",
        "file_size": 1672314,
        "file_type": "pdf"
    }
}
```

2、启动转换任务接口
* URL：ai.pdf2md.convert-url
* 请求示例：
```curl --location 'http://192.168.101.21:38111/api/file/convert2md' \
--header 'X-API-Key: 12345' \
--header 'Content-Type: application/json' \
--data '{
    "file_id":"file-20260111143725-gfNj9jlE"
}'
```
* 响应示例：
```
{
    "task_id": "4d972bab-3c51-4e6c-9472-79d04ddb2312",
    "message": "转换任务已启动",
    "file_id": "file-20260111143725-gfNj9jlE"
}
```

3、获取转换进度及结果接口
* URL：ai.pdf2md.convert-result-url
* 请求示例：
```curl --location 'http://192.168.101.21:38111/api/file/convert2md/result/4d972bab-3c51-4e6c-9472-79d04ddb2312' \
--header 'X-API-Key: 12345'
```
* 响应示例：
（1）进行中
```
{
    "task_id": "4d972bab-3c51-4e6c-9472-79d04ddb2312",
    "file_id": "file-20260111143725-gfNj9jlE",
    "status": "processing",
    "progress": 43,
    "result": null,
    "error": null,
    "start_time": 1768198633.9641507,
    "end_time": null
}
```
（2）完成
```   
{
    "task_id": "4d972bab-3c51-4e6c-9472-79d04ddb2312",
    "file_id": "file-20260111143725-gfNj9jlE",
    "status": "completed",
    "progress": 100,
    "result": {
        "file_id": "file-20260111143725-gfNj9jlE",
        "markdown_content": "\n## 第 1 页\n\n\n...",
        "output_path": "/app/uploads/file-20260111143725-gfNj9jlE_converted_1768198633.md",
        "processing_time": 79.12861967086792,
        "pages_processed": 23,
        "tables_found": 0
    },
    "error": null,
    "start_time": 1768198633.9641507,
    "end_time": 1768198713.0936172
}
```

（3）失败
```
{
  "code": 500,
  "message": "检查记录没有招标或投标文件",
  "data": null
}
```

## 部署

```shell
docker build -t pdf2md:v0.1 .

docker run -d --name pdf2md  -p 38111:18080 -v `pwd`/data:/app/uploads -v `pwd`/logs:/app/logs pdf2md:v0.1 
```

## 贡献代码

欢迎提交Pull Request来贡献代码。在贡献代码之前，请先阅读并遵守项目的许可证。

## 许可证

 Apache 2.0 License