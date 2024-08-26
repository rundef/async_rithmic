.PHONY: protoc test

PROTO_PATH=src/rithmic/protocol_buffers/
UNIT_TESTS_PATH?=tests/unit
INTEGRATION_TESTS_PATH?=tests/integration

protoc:
	$(PROTOC_DIR)protoc -I=$(PROTO_PATH)source --python_out=$(PROTO_PATH) $(PROTO_PATH)source/*.proto

unit-tests:
	PYTHONPATH=./src pytest $(UNIT_TESTS_PATH)

integration-tests:
	PYTHONPATH=./src pytest $(INTEGRATION_TESTS_PATH)
