TARGET=./target
DEST=$(TARGET)/botanist

build: clean_pyc clean
	@echo "building..."
	mkdir -p $(DEST)

	cp -R cron $(DEST)
	cp -R packages $(DEST)
	cp -R webapp $(DEST)
	cp install.sh $(DEST)
	cp README.md $(DEST)
	cd $(TARGET) && tar -czf ./botanist.tar.gz ./botanist
	cd $(TARGET) && rm -rf botanist
	@echo "done."


clean_pyc:
	@echo "cleaning pyc files..."
	@find . -name "*.pyc" -exec rm {} \;


clean:
	@echo "cleaning prior build..."
	rm -rf $(TARGET)
