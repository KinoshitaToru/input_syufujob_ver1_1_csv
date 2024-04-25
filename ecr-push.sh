aws ecr get-login-password --region ap-northeast-1 --profile  kinoshita-syufujob | docker login --username AWS --password-stdin 654654170989.dkr.ecr.ap-northeast-1.amazonaws.com
docker build -t input_syufujob_ver1_csv .
docker tag input_syufujob_ver1_csv:latest 654654170989.dkr.ecr.ap-northeast-1.amazonaws.com/input_syufujob_ver1_csv:latest
docker push 654654170989.dkr.ecr.ap-northeast-1.amazonaws.com/input_syufujob_ver1_csv:latest
aws lambda update-function-code --function-name input_syufujob_ver1_csv --image-uri 654654170989.dkr.ecr.ap-northeast-1.amazonaws.com/input_syufujob_ver1_csv:latest --profile  kinoshita-syufujob --region=ap-northeast-1 --no-cli-pager
