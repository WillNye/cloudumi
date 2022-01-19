resource "aws_vpc" "main_vpc" {
  cidr_block       = "10.${var.attributes}.0.0/16"
  instance_tenancy = "default"

  tags = {
      Name = "main_vpc"
  }
}

resource "aws_internet_gateway" "main_igw" {
  vpc_id = aws_vpc.main_vpc.id

  tags = {
    Name = "main_igw"
  }
}