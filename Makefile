.PHONY: protoc test

PROTO_PATH=src/rithmic/protocol_buffers/
UNIT_TEST_PATH?=tests/unit

protoc:
	$(PROTOC_DIR)protoc -I=$(PROTO_PATH)source --python_out=$(PROTO_PATH) $(PROTO_PATH)source/*.proto

unit-test:
	RITHMIC_ENVIRONMENT_NAME=RITHMIC_TEST RITHMIC_CREDENTIALS_PATH=tests/configs PYTHONPATH=./src pytest $(UNIT_TEST_PATH)
