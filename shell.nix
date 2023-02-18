let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  name = "awap2023";
  buildInputs = [
    pkgs.python3Packages.numpy
  ];
}
