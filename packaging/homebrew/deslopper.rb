# Homebrew formula for deslopper, kept here as the source of truth.
#
# At release, the publish process copies this file into the jv-k/homebrew-tap repo (as
# Formula/deslopper.rb) with `url` and `sha256` filled from the PyPI sdist. Until the first
# release those two fields are placeholders. deslopper has no runtime dependencies, so the
# formula needs no resource stanzas.
class Deslopper < Formula
  include Language::Python::Virtualenv

  desc "Deterministic prose linter for the mechanical tells of machine-generated writing"
  homepage "https://github.com/jv-k/deslopper"
  url "https://files.pythonhosted.org/packages/source/d/deslopper/deslopper-0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "deslopper #{version}", shell_output("#{bin}/deslopper --version")
  end
end
