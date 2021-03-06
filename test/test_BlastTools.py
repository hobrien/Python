from BlastTools import get_taxid

P_venosa_id = 162011
   
def test_get_taxid():
  assert get_taxid('gi|455475748|gb|KC437649.1|') == P_venosa_id 
  assert get_taxid('gi|455475748|gb|KC437649.1') == P_venosa_id 
  assert get_taxid('KC437649') == P_venosa_id
  assert get_taxid('KC437649.1') == P_venosa_id
  assert get_taxid('gi|455475748') == P_venosa_id 
  assert get_taxid('455475748') == P_venosa_id 
