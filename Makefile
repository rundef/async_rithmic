.PHONY: protoc tests

PROTO_PATH=src/rithmic/protocol_buffers/
TESTS_PATH?=tests

protoc:
	$(PROTOC_DIR)protoc -I=$(PROTO_PATH)source --python_out=$(PROTO_PATH) $(PROTO_PATH)source/*.proto

tests:
	PYTHONPATH=. pytest -s -vv $(TESTS_PATH)

