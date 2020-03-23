help:           ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

init:  ## 初始化python环境，并加载测试数据
	python3 -m venv env
	env/bin/python -m pip install -r requirements.txt
	env/bin/python src/manage.py migrate
	env/bin/python src/manage.py loaddata --format yaml fixtures.yaml
	@echo "初始化完成。现在你可以运行：make run 启动后端应用了。"

init2: ## 简单建立 env/bin/python 来直接搭建环境
	mkdir -p env/bin
	ln -s `which python` env/bin/python
	ln -s `which python` env/bin/python3

stop: ## 停止 make prd/ make run 启动的服务
	-lsof -i:9084 | awk 'NR==2{print $$2}' | xargs kill

run: stop ## 运行后端服务(front)
	env/bin/python src/manage.py runserver 9084

prd: stop ## 生产环境运行(backend)
	nohup env/bin/python src/manage.py runserver 9084 2>&1 &

upgrade: ## 升级后端服务代码
	env/bin/python -m pip install -r requirements.txt
	env/bin/python src/manage.py migrate
	# env/bin/python src/manage.py loaddata --format yaml fixtures.yaml
	env/bin/python src/manage.py collectstatic --noinput

dep: ## 部署服务到supervisor与nginx
	-sudo cp deploy/nginx/amoeba_prd.conf /etc/nginx/conf.d/
	-sudo cp deploy/supervisor/amoeba_prd.ini /etc/supervisord.d/

crontab: ## 安装 cron 定时任务
	cd src && ../env/bin/python manage.py installtasks

cloc: ## 代码量统计。请提前安装cloc(brew install cloc)
	cloc --exclude-dir="env,docs,logs,include,CMakeFiles,dist,static,theme,build,staticfiles" --exclude-ext="json,xml,yaml,yml,md" .

docker-build: ## docker build
	docker build -f docker/Dockerfile -t ccr.ccs.tencentyun.com/tjhb/amoeba:latest .

docker-run: ## docker run
	if [ -f .env ]; then docker run --env-file=.env --rm -it -p 9084:9084 ccr.ccs.tencentyun.com/tjhb/amoeba ${CMD} ; \
	else docker run --rm -it -p 9084:9084 ccr.ccs.tencentyun.com/tjhb/amoeba ${CMD} ; fi

docker-release: ## merge master to docker
	bumpversion patch
	# 	-git branch docker
	- git branch -d docker
	git checkout -b docker origin/docker
	git merge master
	git checkout master
	git push origin docker
	git push origin master
	bumpversion patch --dry-run --list | grep current

doc: ## 构建 doc 文档, 并查看
	cd docs && make open

epub: ## 构建 epub 模式文档
	cd docs && make epub && open -a finder _build/epub

pdf: ## 构建 pdf 文档
	cd docs && make pdf

doc-clean: ## 清理 doc 构建数据
	cd docs && make clean

CODE_DIR ?= .
docker-test: ## test docker
	docker build -f ./docker/Dockerfile . -t ccr.ccs.tencentyun.com/tjhb/amoeba:latest

test: ##　运行测试用例
	PYTHONPATH=./src pytest

%:  ## cli命令
	env/bin/python "cli.py" $(MAKECMDGOALS)
