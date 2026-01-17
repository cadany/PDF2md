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
   - `/api/file/convert2md/stop`：传入任务id，停止文件转换任务。
   - `/api/file/convert2md/progress`：传入任务id，返回文件转换任务进度。
   - `/api/file/convert2md/result`：传入任务id，返回文件转换任务结果。

## 部署

```shell
docker build -t pdf2md:v0.1 .

docker run -d --name pdf2md  -p 38111:18080 -v `pwd`/data:/app/uploads -v `pwd`/logs:/app/logs pdf2md:v0.1 
```

## 贡献代码

欢迎提交Pull Request来贡献代码。在贡献代码之前，请先阅读并遵守项目的许可证。

## 许可证

 Apache 2.0 License