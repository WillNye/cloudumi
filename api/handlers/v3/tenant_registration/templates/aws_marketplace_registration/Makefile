.PHONY: upload_registration_page
upload_registration_page:
	@AWS_PROFILE=prod/production_administrator aws s3 cp . s3://marketplace-saas-noq-2-static-html/ --recursive --exclude "Makefile"
