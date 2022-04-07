# Releasing imtvault

You must have installed the dataset via
```shell
pip install -e .
```
preferably in a separate virtual environment.

- Update the tex file submodule:
  ```shell
  cd raw/raw_texfiles/
  git pull origin
  cd ../..
  ```
- Extract the examples from the TeX files running
  ```shell
  cldfbench imtvault.extract --glottolog ~/projects/glottolog/glottolog --glottolog-version v4.5
  ```
- Recreate the CLDF running
  ```shell
  cldfbench makecldf --with-cldfreadme --with-zenodo cldfbench_imtvault.py --glottolog-version v4.5
  ```
- Recreate the README running
  ```shell
  cldfbench imtvault.readme
  ```
- Commit and push changes to GitHub
- Create a release on GitHub, thereby pushing the version to Zenodo.
